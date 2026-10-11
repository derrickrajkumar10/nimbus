import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nimbus_app/contracts/nimbus.dart';
import 'package:nimbus_app/ui/screens/home_screen.dart';

import '../support/fake_api.dart';
import '../support/fixtures.dart';
import '../support/host.dart';

FakeApi _api() => FakeApi(places: [
      place('pl-bike', 'Bike parking', ['27480309-1'], kind: SavedPlaceKind.VEHICLE_PARKING),
      place('pl-home', 'Home', ['27480309-4']),
      place('pl-office', 'Office', ['27320162-0'], kind: SavedPlaceKind.OFFICE),
    ]);

void main() {
  testWidgets('rows are ordered low, likely, flooded top to bottom', (tester) async {
    await pumpScreen(tester, const HomeScreen(), api: _api(), risk: fixtureSnapshot());
    final office = tester.getTopLeft(find.text('Office')).dy;
    final home = tester.getTopLeft(find.text('Home')).dy;
    final bike = tester.getTopLeft(find.text('Bike parking')).dy;
    expect(office, lessThan(home));
    expect(home, lessThan(bike));
  });

  testWidgets('headline says 2 of your places need you now', (tester) async {
    await pumpScreen(tester, const HomeScreen(), api: _api(), risk: fixtureSnapshot());
    expect(find.text('2 of your places need you now'), findsOneWidget);
    expect(find.textContaining('Replay · Cyclone Michaung · 4 Dec 02:00'), findsOneWidget);
  });

  testWidgets('a row shows the last alert body over the reason', (tester) async {
    await pumpScreen(tester, const HomeScreen(),
        api: _api(),
        risk: fixtureSnapshot(),
        prefs: {'last_alerts': '{"pl-bike": "Move your bike to Vijayanagar 1st Main Road"}'});
    expect(find.text('Move your bike to Vijayanagar 1st Main Road'), findsOneWidget);
  });

  testWidgets('places without Segments or risk say so', (tester) async {
    final api = FakeApi(places: [place('pl-far', 'Far away', []), place('pl-new', 'Unscored', ['99999-0'])]);
    await pumpScreen(tester, const HomeScreen(), api: api, risk: fixtureSnapshot());
    expect(find.text('No streets nearby'), findsOneWidget);
    expect(find.text('No data yet'), findsOneWidget);
    expect(find.text('All your places are clear'), findsOneWidget);
  });

  testWidgets('stale snapshot shows the offline tag', (tester) async {
    await pumpScreen(tester, const HomeScreen(), api: _api(), risk: fixtureSnapshot(stale: true));
    expect(find.text('Offline · updated 02:00'), findsOneWidget);
  });

  testWidgets('no overflow at 320x640 in ta', (tester) async {
    tester.view.physicalSize = const Size(320, 640);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    await pumpScreen(tester, const HomeScreen(), api: _api(), risk: fixtureSnapshot(), lang: 'ta',
        prefs: {'last_alerts': '{"pl-bike": "உங்கள் பைக்கை விஜயநகர் 1வது மெயின் ரோட்டுக்கு நகர்த்துங்கள்"}'});
    expect(tester.takeException(), isNull);
    expect(find.textContaining('உங்கள் இடங்களில் 2 இடங்களுக்கு'), findsOneWidget);
  });
}
