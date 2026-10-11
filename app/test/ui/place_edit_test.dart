import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nimbus_app/contracts/nimbus.dart';
import 'package:nimbus_app/domain/place_view.dart';
import 'package:nimbus_app/state/providers.dart';
import 'package:nimbus_app/ui/screens/place_edit_screen.dart';
import 'package:nimbus_app/ui/widgets/tide_map.dart';

import '../support/fake_api.dart';
import '../support/host.dart';

void main() {
  final noMap = mapEnabledProvider.overrideWithValue(false);

  // The waves never settle, so step past dialog and route transitions.
  Future<void> settle(WidgetTester tester) async {
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
  }

  // The fixture API's delays are real timers: run direct calls outside fake time.
  Future<List<PlaceView>> stored(WidgetTester tester, FakeApi api) async => (await tester.runAsync(api.savedPlaces))!;

  Future<void> seed(WidgetTester tester, FakeApi api, String id) => tester.runAsync(
    () => api.putPlace(id, label: 'Home', kind: SavedPlaceKind.HOME, location: velachery, runIds: const [demoRun]),
  );

  Future<void> tapText(WidgetTester tester, String text) async {
    await tester.ensureVisible(find.text(text));
    await tester.pump();
    await tester.tap(find.text(text));
  }

  Future<void> nameAndSave(WidgetTester tester, String label) async {
    await tester.enterText(find.byType(TextField), label);
    await tapText(tester, 'Save');
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));
  }

  setUp(() {
    final view = TestWidgetsFlutterBinding.instance.platformDispatcher.views.first;
    view.physicalSize = const Size(390, 844);
    view.devicePixelRatio = 1;
  });
  tearDown(() => TestWidgetsFlutterBinding.instance.platformDispatcher.views.first.reset());

  testWidgets('save sends runIds [replay-michaung] in the demo run', (tester) async {
    final api = FakeApi();
    await pumpScreen(tester, const PlaceEditScreen(), api: api, overrides: [noMap]);
    await tester.tap(find.text('Office'));
    await nameAndSave(tester, 'Work');

    final saved = (await stored(tester, api)).single;
    expect(saved.runIds, [demoRun]);
    expect(saved.id, matches(RegExp(r'^pl-[0-9a-f-]{36}$')));
    expect(saved.place.label, 'Work');
    expect(saved.place.kind, SavedPlaceKind.OFFICE);
    expect(saved.place.radiusM, 150);
    expect((saved.place.location.lat, saved.place.location.lon), (velachery.lat, velachery.lon));
  });

  testWidgets('too_many_places shows the message', (tester) async {
    final api = FakeApi();
    for (var i = 0; i < 20; i++) {
      await seed(tester, api, 'pl-$i');
    }
    await pumpScreen(tester, const PlaceEditScreen(), api: api, overrides: [noMap]);
    await nameAndSave(tester, 'One more');

    expect(find.text('You can save up to 20 places. Remove one to add another.'), findsOneWidget);
    expect(await stored(tester, api), hasLength(20));
  });

  testWidgets('in live the pin starts at the GPS position', (tester) async {
    final api = FakeApi();
    final here = GeoPoint(lat: 12.99, lon: 80.22);
    await pumpScreen(
      tester,
      const PlaceEditScreen(),
      api: api,
      runId: liveRun,
      overrides: [noMap, currentPositionProvider.overrideWith((ref) async => here)],
    );
    await nameAndSave(tester, 'Home');

    final saved = (await stored(tester, api)).single;
    expect((saved.place.location.lat, saved.place.location.lon), (here.lat, here.lon));
    expect(saved.runIds, [liveRun]);
  });

  testWidgets('delete asks first, then removes the place', (tester) async {
    final api = FakeApi();
    await seed(tester, api, 'pl-home');
    await pumpScreen(
      tester,
      const PlaceEditScreen(placeId: 'pl-home'),
      api: api,
      overrides: [noMap],
    );
    expect(find.widgetWithText(TextField, 'Home'), findsOneWidget);

    await tapText(tester, 'Delete');
    await settle(tester);
    expect(find.text('Remove this place?'), findsOneWidget);
    await tester.tap(find.text('Cancel'));
    await settle(tester);
    expect(await stored(tester, api), hasLength(1));

    await tapText(tester, 'Delete');
    await settle(tester);
    await tester.tap(find.text('Remove'));
    await settle(tester);
    expect(await stored(tester, api), isEmpty);
  });
}
