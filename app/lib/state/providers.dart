import 'dart:async';
import 'dart:convert';

import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart' show Locale;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../config.dart';
import '../contracts/nimbus.dart';
import '../data/api_exception.dart';
import '../data/fixture_api.dart';
import '../data/http_api.dart';
import '../data/nimbus_api.dart';
import '../domain/place_view.dart';

const liveRun = 'live';
const demoRun = 'replay-michaung';

/// Overridden in `main` once SharedPreferences has loaded.
final prefsProvider = Provider<SharedPreferences>((ref) => throw UnimplementedError('override prefsProvider'));

/// Overridden in `main` with the stored or new install id.
final installIdProvider = Provider<String>((ref) => throw UnimplementedError('override installIdProvider'));

final configProvider = Provider<AppConfig>((ref) => AppConfig.fromEnvironment());

final apiProvider = Provider<NimbusApi>((ref) {
  final config = ref.watch(configProvider);
  final base = config.apiBase;
  if (base == null) return FixtureNimbusApi(rootBundle, prefs: ref.watch(prefsProvider));
  return HttpNimbusApi(base, ref.watch(installIdProvider));
});

/// Asks for notification permission; replaced in tests. Task 10 wires FCM.
final notificationPermissionProvider = Provider<Future<void> Function()>((ref) => () async {});

/// A small persisted string setting.
abstract class _PrefNotifier extends Notifier<String> {
  String get key;
  String get fallback;

  @override
  String build() => ref.watch(prefsProvider).getString(key) ?? fallback;

  void set(String value) {
    state = value;
    ref.read(prefsProvider).setString(key, value);
  }
}

/// The Run this install follows: `live`, or the demo Replay.
class RunIdNotifier extends _PrefNotifier {
  @override
  String get key => 'run_id';
  @override
  String get fallback => liveRun;

  void toggleDemo() => set(state == demoRun ? liveRun : demoRun);
}

final runIdProvider = NotifierProvider<RunIdNotifier, String>(RunIdNotifier.new);

/// `en` or `ta`.
class LanguageNotifier extends _PrefNotifier {
  @override
  String get key => 'lang';
  @override
  String get fallback => 'en';
}

final languageProvider = NotifierProvider<LanguageNotifier, String>(LanguageNotifier.new);

final localeProvider = Provider<Locale>((ref) => Locale(ref.watch(languageProvider)));

/// Segments are static, so they're fetched once and kept.
final segmentsProvider = FutureProvider<List<Segment>>((ref) => ref.watch(apiProvider).segments());

final segmentByIdProvider = FutureProvider<Map<String, Segment>>((ref) async => {
      for (final s in await ref.watch(segmentsProvider.future)) s.segmentId: s,
    });

/// The latest risk per Segment. [stale] means the last poll failed and this
/// is the last good data; [simTime] is its storm time.
class RiskSnapshot {
  const RiskSnapshot({required this.bySegment, required this.simTime, this.stale = false});

  static const empty = RiskSnapshot(bySegment: {}, simTime: null);

  factory RiskSnapshot.of(List<SegmentRisk> rows) {
    DateTime? latest;
    for (final r in rows) {
      if (latest == null || r.simTime.isAfter(latest)) latest = r.simTime;
    }
    return RiskSnapshot(bySegment: {for (final r in rows) r.segmentId: r}, simTime: latest);
  }

  final Map<String, SegmentRisk> bySegment;
  final DateTime? simTime;
  final bool stale;

  RiskSnapshot asStale() => RiskSnapshot(bySegment: bySegment, simTime: simTime, stale: true);
}

final riskPollIntervalProvider = Provider<Duration>((ref) => const Duration(seconds: 5));

/// Polls `GET /risk` while something watches it. A failed poll never errors
/// the stream: it re-emits the last good snapshot marked stale.
final riskProvider = StreamProvider.autoDispose<RiskSnapshot>((ref) async* {
  final api = ref.watch(apiProvider);
  final runId = ref.watch(runIdProvider);
  final interval = ref.watch(riskPollIntervalProvider);
  var alive = true;
  ref.onDispose(() => alive = false);
  var last = RiskSnapshot.empty;
  while (alive) {
    try {
      last = RiskSnapshot.of(await api.risk(runId));
      yield last;
    } on ApiException {
      yield last.asStale();
    }
    await Future<void>.delayed(interval);
  }
});

final hazardsProvider = FutureProvider.autoDispose<List<Hazard>>(
    (ref) => ref.watch(apiProvider).hazards(ref.watch(runIdProvider)));

final readingsProvider = FutureProvider.autoDispose<List<Reading>>(
    (ref) => ref.watch(apiProvider).readings(ref.watch(runIdProvider)));

/// This install's Saved Places.
class PlacesNotifier extends AsyncNotifier<List<PlaceView>> {
  @override
  Future<List<PlaceView>> build() => ref.watch(apiProvider).savedPlaces();

  Future<PlaceView> save({
    required String placeId,
    required String label,
    required SavedPlaceKind kind,
    required GeoPoint location,
    double? radiusM,
    required List<String> runIds,
  }) async {
    final saved = await ref.read(apiProvider).putPlace(placeId,
        label: label, kind: kind, location: location, radiusM: radiusM, runIds: runIds);
    final current = state.value ?? const <PlaceView>[];
    state = AsyncData([
      for (final p in current)
        if (p.id != placeId) p,
      saved,
    ]);
    return saved;
  }

  Future<void> remove(String placeId) async {
    await ref.read(apiProvider).deletePlace(placeId);
    state = AsyncData([
      for (final p in state.value ?? const <PlaceView>[])
        if (p.id != placeId) p,
    ]);
  }
}

final placesProvider = AsyncNotifierProvider<PlacesNotifier, List<PlaceView>>(PlacesNotifier.new);

/// The body of the last alert received per Saved Place: the action line.
class LastAlertNotifier extends Notifier<Map<String, String>> {
  static const key = 'last_alerts';

  @override
  Map<String, String> build() {
    final raw = ref.watch(prefsProvider).getString(key);
    return raw == null ? const {} : Map<String, String>.from(jsonDecode(raw) as Map);
  }

  void record(String placeId, String body) {
    state = {...state, placeId: body};
    ref.read(prefsProvider).setString(key, jsonEncode(state));
  }
}

final lastAlertProvider = NotifierProvider<LastAlertNotifier, Map<String, String>>(LastAlertNotifier.new);

/// Whether the one-time intro has played.
final introSeenProvider = Provider<bool>((ref) => ref.watch(prefsProvider).getBool('intro_seen') ?? false);
