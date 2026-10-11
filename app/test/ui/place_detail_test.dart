import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nimbus_app/ui/screens/place_detail_screen.dart';
import 'package:nimbus_app/ui/widgets/tide_map.dart';

import '../support/fake_api.dart';
import '../support/fixtures.dart';
import '../support/host.dart';

FakeApi _api() => FakeApi(places: [place('pl-home', 'Home', ['27480309-4'])]);

void main() {
  final noMap = [mapEnabledProvider.overrideWithValue(false)];

  testWidgets('shows the band, countdown, reasons and the fallback action', (tester) async {
    await pumpScreen(tester, const PlaceDetailScreen(placeId: 'pl-home'),
        api: _api(), risk: fixtureSnapshot(), overrides: noMap);
    expect(find.text('Likely'), findsOneWidget);
    expect(find.text('Floods in about 30m'), findsOneWidget);
    expect(find.text('Move your vehicle to higher ground'), findsOneWidget);
    expect(find.text('Show me the way'), findsOneWidget);
  });

  testWidgets('the last alert body is the action line', (tester) async {
    await pumpScreen(tester, const PlaceDetailScreen(placeId: 'pl-home'),
        api: _api(),
        risk: fixtureSnapshot(),
        overrides: noMap,
        prefs: {'last_alerts': '{"pl-home": "Park on Vijayanagar 1st Main Road"}'});
    expect(find.text('Park on Vijayanagar 1st Main Road'), findsOneWidget);
    expect(find.text('Move your vehicle to higher ground'), findsNothing);
  });

  testWidgets('a place with no Segments says so', (tester) async {
    await pumpScreen(tester, const PlaceDetailScreen(placeId: 'pl-far'),
        api: FakeApi(places: [place('pl-far', 'Far away', [])]), risk: fixtureSnapshot(), overrides: noMap);
    expect(find.text('No streets nearby'), findsOneWidget);
  });

  testWidgets('no overflow at 320x640 in ta', (tester) async {
    tester.view.physicalSize = const Size(320, 640);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    await pumpScreen(tester, const PlaceDetailScreen(placeId: 'pl-home'),
        api: _api(), risk: fixtureSnapshot(), overrides: noMap, lang: 'ta');
    expect(tester.takeException(), isNull);
  });

  testWidgets('the panel fills the screen under the map and takes taps', (tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    await pumpScreen(tester, const PlaceDetailScreen(placeId: 'pl-home'),
        api: _api(), risk: fixtureSnapshot(), overrides: noMap);
    expect(tester.getRect(find.byType(SingleChildScrollView)).bottom, 844);
    await tester.tap(find.text('Show me the way'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    expect(find.text('/route'), findsOneWidget);
  });
}
