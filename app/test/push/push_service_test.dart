import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:nimbus_app/push/push_service.dart';

import '../support/fake_api.dart';
import '../support/fixtures.dart';

/// FCM and local notifications, driven by the test.
class FakePlatform implements PushPlatform {
  String? currentToken = 'tok-1';
  final refresh = StreamController<String>.broadcast();
  final foregroundIn = StreamController<PushMessage>.broadcast();
  final openedIn = StreamController<PushMessage>.broadcast();
  PushMessage? launch;
  final shown = <PushMessage>[];

  @override
  Future<String?> token() async => currentToken;
  @override
  Stream<String> get tokenRefresh => refresh.stream;
  @override
  Stream<PushMessage> get foreground => foregroundIn.stream;
  @override
  Stream<PushMessage> get opened => openedIn.stream;
  @override
  Future<PushMessage?> initial() async => launch;
  @override
  Future<void> show(PushMessage m) async => shown.add(m);
}

/// Records `registerDevice` calls.
class DeviceApi extends FakeApi {
  final registered = <(String, String)>[];

  @override
  Future<void> registerDevice(String fcmToken, String language) async => registered.add((fcmToken, language));
}

void main() {
  final places = [
    place('pl-home', 'Home', ['27480309-4']),
    place('pl-bike', 'Bike parking', ['27480309-2']),
  ];
  const body = 'Water likely on Velachery Main Road by 6 pm. Park on Vijayanagar 1st Main Road.';

  test('handlePush routes to the matching place and stores the body', () {
    final a = handlePush({'alert_id': 'al-1', 'run_id': 'live', 'segment_id': '27480309-2', 'band': 'likely'}, body, places);
    expect(a.route, '/place/pl-bike');
    expect(a.placeId, 'pl-bike');
    expect(a.storeBody, body);
  });

  test('handlePush routes to /home when nothing matches', () {
    for (final data in [
      {'alert_id': 'al-1', 'segment_id': '11111-0'},
      {'alert_id': 'al-1'},
    ]) {
      final a = handlePush(data, body, places);
      expect(a.route, '/home');
      expect(a.placeId, isNull);
      expect(a.storeBody, isNull);
    }
    expect(handlePush({'segment_id': '27480309-2'}, body, const []).route, '/home');
  });

  group('PushService', () {
    late FakePlatform platform;
    late DeviceApi api;
    late List<String> routes;
    late Map<String, String> stored;
    late PushService push;

    setUp(() {
      platform = FakePlatform();
      api = DeviceApi();
      routes = [];
      stored = {};
      push = PushService(
        api,
        platform: platform,
        places: () async => places,
        storeAlert: (id, b) => stored[id] = b,
        navigate: routes.add,
      );
    });

    test('registers the token with the language, again on refresh and on a language change', () async {
      await push.start('ta');
      platform.refresh.add('tok-2');
      await pumpEventQueue();
      await push.setLanguage('en');
      expect(api.registered, [('tok-1', 'ta'), ('tok-2', 'ta'), ('tok-2', 'en')]);
    });

    test('the same token and language register once', () async {
      await push.start('en');
      platform.refresh.add('tok-1');
      await pumpEventQueue();
      expect(api.registered, [('tok-1', 'en')]);
    });

    test('a foreground push is shown and its body stored for the place', () async {
      await push.start('en');
      final m = PushMessage(data: {'segment_id': '27480309-4'}, title: 'NIMBUS', body: body);
      platform.foregroundIn.add(m);
      await pumpEventQueue();
      expect(platform.shown, [m]);
      expect(stored, {'pl-home': body});
      expect(routes, isEmpty);
    });

    test('a tapped push opens its place, and a cold start with no match opens Home', () async {
      platform.launch = PushMessage(data: {'segment_id': '99999-0'}, body: body);
      await push.start('en');
      platform.openedIn.add(PushMessage(data: {'segment_id': '27480309-2'}, body: body));
      await pumpEventQueue();
      expect(routes, ['/home', '/place/pl-bike']);
      expect(stored, {'pl-bike': body});
    });
  });
}
