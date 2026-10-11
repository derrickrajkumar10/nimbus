import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nimbus_app/data/api_exception.dart';
import 'package:nimbus_app/state/providers.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../support/fake_api.dart';

Future<ProviderContainer> _container(FakeApi api, {Map<String, Object> prefs = const {}}) async {
  SharedPreferences.setMockInitialValues(prefs);
  final p = await SharedPreferences.getInstance();
  final c = ProviderContainer(overrides: [
    prefsProvider.overrideWithValue(p),
    apiProvider.overrideWithValue(api),
    riskPollIntervalProvider.overrideWithValue(const Duration(milliseconds: 5)),
  ]);
  addTearDown(c.dispose);
  return c;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('riskProvider re-emits the last snapshot as stale when the API throws', () async {
    final api = FakeApi();
    final fixtureRows = await api.risk('replay-michaung');
    api.riskCalls = 0;
    api.onRisk = (runId, call) async =>
        call == 1 ? fixtureRows : throw const ApiException.offline();
    final c = await _container(api, prefs: {'run_id': 'replay-michaung'});

    final snapshots = <RiskSnapshot>[];
    final two = Completer<void>();
    c.listen<AsyncValue<RiskSnapshot>>(riskProvider, (_, next) {
      final v = next.value;
      if (v != null) snapshots.add(v);
      if (snapshots.length == 2 && !two.isCompleted) two.complete();
    }, fireImmediately: true);
    await two.future.timeout(const Duration(seconds: 2));

    expect(snapshots[0].stale, isFalse);
    expect(snapshots[0].bySegment, hasLength(21));
    expect(snapshots[1].stale, isTrue);
    expect(snapshots[1].bySegment, hasLength(21));
    expect(snapshots[1].simTime, snapshots[0].simTime);
    expect(snapshots[0].simTime, DateTime.parse('2023-12-04T02:00:00+05:30'));
  });

  test('riskProvider is stale and empty when the first call fails', () async {
    final api = FakeApi()..onRisk = (_, _) async => throw const ApiException.offline();
    final c = await _container(api);
    final first = Completer<RiskSnapshot>();
    c.listen<AsyncValue<RiskSnapshot>>(riskProvider, (_, next) {
      final v = next.value;
      if (v != null && !first.isCompleted) first.complete(v);
    }, fireImmediately: true);
    final snap = await first.future.timeout(const Duration(seconds: 2));
    expect(snap.stale, isTrue);
    expect(snap.bySegment, isEmpty);
  });

  test('runIdProvider persists replay-michaung', () async {
    final api = FakeApi();
    final c = await _container(api);
    expect(c.read(runIdProvider), 'live');
    c.read(runIdProvider.notifier).set('replay-michaung');
    expect(c.read(runIdProvider), 'replay-michaung');

    final prefs = c.read(prefsProvider);
    expect(prefs.getString('run_id'), 'replay-michaung');
    final again = ProviderContainer(overrides: [
      prefsProvider.overrideWithValue(prefs),
      apiProvider.overrideWithValue(api),
    ]);
    addTearDown(again.dispose);
    expect(again.read(runIdProvider), 'replay-michaung');
  });

  test('lastAlertProvider persists the body per place', () async {
    final c = await _container(FakeApi());
    c.read(lastAlertProvider.notifier).record('pl-bike', 'Move your bike to Vijayanagar 1st Main Road');
    expect(c.read(lastAlertProvider), {'pl-bike': 'Move your bike to Vijayanagar 1st Main Road'});
    expect(c.read(prefsProvider).getString('last_alerts'), contains('pl-bike'));
  });
}
