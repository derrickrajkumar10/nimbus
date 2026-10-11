import 'dart:async';
import 'dart:convert';

import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../app.dart';
import '../data/nimbus_api.dart';
import '../domain/alert_routing.dart';
import '../domain/place_view.dart';
import '../state/providers.dart';
import '../ui/routes.dart';

/// What a push leads to: where a tap goes, and the body to keep as the
/// place's action line.
class PushAction {
  const PushAction({required this.route, this.placeId, this.storeBody});

  final String route;
  final String? placeId;
  final String? storeBody;
}

/// The Saved Place whose Segments contain the push's `segment_id`, or Home.
PushAction handlePush(Map<String, dynamic> data, String? body, List<PlaceView> places) {
  final placeId = placeIdForAlert(data, places);
  if (placeId == null) return const PushAction(route: Routes.home);
  return PushAction(route: Routes.place(placeId), placeId: placeId, storeBody: body);
}

/// A push as the app sees it: the sender's title and body, and its `data`
/// (`alert_id`, `run_id`, optionally `segment_id` and `band`).
class PushMessage {
  const PushMessage({required this.data, this.title, this.body});

  final Map<String, dynamic> data;
  final String? title;
  final String? body;

  factory PushMessage.fromRemote(RemoteMessage m) =>
      PushMessage(data: m.data, title: m.notification?.title, body: m.notification?.body);

  factory PushMessage.fromJson(Map<String, dynamic> j) => PushMessage(
        data: Map<String, dynamic>.from(j['data'] as Map),
        title: j['title'] as String?,
        body: j['body'] as String?,
      );

  Map<String, dynamic> toJson() => {'data': data, 'title': title, 'body': body};
}

/// FCM plus local notifications, behind one seam so the service is testable.
abstract interface class PushPlatform {
  Future<String?> token();
  Stream<String> get tokenRefresh;

  /// Pushes that arrive while the app is open.
  Stream<PushMessage> get foreground;

  /// Pushes the user tapped while the app was running.
  Stream<PushMessage> get opened;

  /// The push the app was launched from, if any.
  Future<PushMessage?> initial();

  /// Shows a push as a notification (FCM shows nothing in the foreground).
  Future<void> show(PushMessage m);
}

/// Registers this install for alerts and routes the ones that arrive.
class PushService {
  PushService(
    this.api, {
    required this.platform,
    required this.places,
    required this.storeAlert,
    required this.navigate,
  });

  final NimbusApi api;
  final PushPlatform platform;
  final Future<List<PlaceView>> Function() places;
  final void Function(String placeId, String body) storeAlert;
  final void Function(String route) navigate;

  String? _token;
  String _language = 'en';

  /// What the API last accepted, so a refresh with the same token (FCM
  /// sends one on a fresh install) isn't sent twice.
  (String, String)? _registered;
  final _subs = <StreamSubscription<Object?>>[];

  Future<void> start(String language) async {
    _language = language;
    _subs
      ..add(platform.tokenRefresh.listen(_register))
      ..add(platform.foreground.listen(_onForeground))
      ..add(platform.opened.listen(_onOpened));
    final token = await platform.token();
    if (token != null) await _register(token);
    final launch = await platform.initial();
    if (launch != null) await _onOpened(launch);
  }

  /// Pushes arrive in the device's language, so the API is told on a switch.
  Future<void> setLanguage(String language) async {
    if (language == _language) return;
    _language = language;
    final token = _token;
    if (token != null) await _register(token);
  }

  Future<void> _register(String token) async {
    _token = token;
    final next = (token, _language);
    if (next == _registered) return;
    try {
      await api.registerDevice(token, _language);
      _registered = next;
    } catch (e) {
      // Retried on the next refresh or language change.
      debugPrint('registerDevice failed: $e');
    }
  }

  Future<PushAction> _act(PushMessage m) async {
    List<PlaceView> known;
    try {
      known = await places();
    } catch (_) {
      known = const [];
    }
    final action = handlePush(m.data, m.body, known);
    final id = action.placeId;
    final body = action.storeBody;
    if (id != null && body != null) storeAlert(id, body);
    return action;
  }

  Future<void> _onForeground(PushMessage m) async {
    await _act(m);
    await platform.show(m);
  }

  Future<void> _onOpened(PushMessage m) async => navigate((await _act(m)).route);

  void dispose() {
    for (final s in _subs) {
      s.cancel();
    }
  }
}

const _channel = AndroidNotificationChannel('alerts', 'Flood alerts',
    description: 'Water expected at your places', importance: Importance.high);

/// The real platform: Firebase Messaging, with foreground pushes shown on
/// the `alerts` channel through flutter_local_notifications.
class FirebasePushPlatform implements PushPlatform {
  final _messaging = FirebaseMessaging.instance;
  final _local = FlutterLocalNotificationsPlugin();
  final _tapped = StreamController<PushMessage>.broadcast();
  var _ready = false;

  Future<void> _init() async {
    if (_ready) return;
    _ready = true;
    await _local.initialize(
      settings: const InitializationSettings(android: AndroidInitializationSettings('@mipmap/ic_launcher')),
      onDidReceiveNotificationResponse: (r) {
        final m = _decode(r.payload);
        if (m != null) _tapped.add(m);
      },
    );
    await _local
        .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(_channel);
  }

  /// Asks for the Android 13+ notification permission (onboarding's "Allow alerts").
  Future<void> requestPermission() async {
    await _init();
    await _messaging.requestPermission();
  }

  @override
  Future<String?> token() async {
    await _init();
    return _messaging.getToken();
  }

  @override
  Stream<String> get tokenRefresh => _messaging.onTokenRefresh;

  @override
  Stream<PushMessage> get foreground => FirebaseMessaging.onMessage.map(PushMessage.fromRemote);

  @override
  Stream<PushMessage> get opened =>
      StreamGroupLite.merge([FirebaseMessaging.onMessageOpenedApp.map(PushMessage.fromRemote), _tapped.stream]);

  @override
  Future<PushMessage?> initial() async {
    await _init();
    final remote = await _messaging.getInitialMessage();
    if (remote != null) return PushMessage.fromRemote(remote);
    final launch = await _local.getNotificationAppLaunchDetails();
    if (launch?.didNotificationLaunchApp ?? false) return _decode(launch!.notificationResponse?.payload);
    return null;
  }

  @override
  Future<void> show(PushMessage m) => _local.show(
        id: m.data['alert_id']?.hashCode ?? m.hashCode,
        title: m.title,
        body: m.body,
        notificationDetails: NotificationDetails(
          android: AndroidNotificationDetails(_channel.id, _channel.name,
              channelDescription: _channel.description,
              importance: Importance.high,
              priority: Priority.high,
              styleInformation: BigTextStyleInformation(m.body ?? '')),
        ),
        payload: jsonEncode(m.toJson()),
      );

  static PushMessage? _decode(String? payload) {
    if (payload == null) return null;
    try {
      return PushMessage.fromJson(jsonDecode(payload) as Map<String, dynamic>);
    } catch (_) {
      return null;
    }
  }
}

/// Merges broadcast streams without pulling in package:async.
abstract final class StreamGroupLite {
  static Stream<T> merge<T>(List<Stream<T>> streams) {
    late final StreamController<T> out;
    final subs = <StreamSubscription<T>>[];
    out = StreamController<T>.broadcast(
      onListen: () => subs.addAll(streams.map((s) => s.listen(out.add, onError: out.addError))),
      onCancel: () {
        for (final s in subs) {
          s.cancel();
        }
        subs.clear();
      },
    );
    return out.stream;
  }
}

/// True once `Firebase.initializeApp` succeeded in `main`. Without
/// `google-services.json` the app runs with push off.
final firebaseReadyProvider = Provider<bool>((ref) => false);

final firebasePlatformProvider = Provider<FirebasePushPlatform?>(
    (ref) => ref.watch(firebaseReadyProvider) ? FirebasePushPlatform() : null);

/// Null when Firebase isn't set up.
final pushServiceProvider = Provider<PushService?>((ref) {
  final platform = ref.watch(firebasePlatformProvider);
  if (platform == null) return null;
  final push = PushService(
    ref.watch(apiProvider),
    platform: platform,
    places: () => ref.read(placesProvider.future),
    storeAlert: (id, body) => ref.read(lastAlertProvider.notifier).record(id, body),
    navigate: (route) {
      final nav = rootNavigatorKey.currentState;
      if (nav == null) return;
      nav.popUntil((r) => r.isFirst);
      if (route != Routes.home) nav.pushNamed(route);
    },
  );
  ref.onDispose(push.dispose);
  return push;
});
