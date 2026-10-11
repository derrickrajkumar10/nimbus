import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nimbus_app/app.dart';
import 'package:nimbus_app/contracts/nimbus.dart';
import 'package:nimbus_app/state/providers.dart';
import 'package:nimbus_app/ui/screens/home_screen.dart';
import 'package:nimbus_app/ui/screens/intro_screen.dart';
import 'package:nimbus_app/ui/screens/onboarding_screen.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../support/fake_api.dart';

Future<void> _launch(WidgetTester tester, SharedPreferences prefs, FakeApi api) async {
  await tester.pumpWidget(ProviderScope(
    overrides: [
      prefsProvider.overrideWithValue(prefs),
      apiProvider.overrideWithValue(api),
      notificationPermissionProvider.overrideWithValue(() async {}),
    ],
    child: const NimbusApp(),
  ));
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 50));
}

/// A new app on the same prefs: what the next cold start sees.
Future<void> _relaunch(WidgetTester tester, SharedPreferences prefs, FakeApi api) async {
  await tester.pumpWidget(const SizedBox());
  await _launch(tester, prefs, api);
}

void main() {
  late SharedPreferences prefs;
  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    prefs = await SharedPreferences.getInstance();
  });

  testWidgets('intro plays once: Skip sets the flag and goes to onboarding', (tester) async {
    final api = FakeApi();
    await _launch(tester, prefs, api);
    expect(find.byType(IntroScreen), findsOneWidget);

    await tester.tap(find.text('Skip'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 500));
    expect(find.byType(OnboardingScreen), findsOneWidget);
    expect(prefs.getBool('intro_seen'), isTrue);

    await _relaunch(tester, prefs, api);
    expect(find.byType(IntroScreen), findsNothing);
    expect(find.byType(OnboardingScreen), findsOneWidget);
  });

  testWidgets('intro finishes by itself after about 6 s', (tester) async {
    final api = FakeApi();
    await _launch(tester, prefs, api);
    expect(find.text('NIMBUS'), findsOneWidget);
    await tester.pump(const Duration(seconds: 3));
    expect(find.byType(IntroScreen), findsOneWidget);
    await tester.pump(const Duration(seconds: 4));
    await tester.pump(const Duration(milliseconds: 500));
    expect(find.byType(OnboardingScreen), findsOneWidget);
    expect(prefs.getBool('intro_seen'), isTrue);
  });

  testWidgets('a launch with places goes to home', (tester) async {
    await prefs.setBool('intro_seen', true);
    final api = FakeApi();
    await tester.runAsync(() => api.putPlace('pl-1',
        label: 'Home',
        kind: SavedPlaceKind.HOME,
        location: GeoPoint(lat: 12.975, lon: 80.219),
        runIds: ['live']));
    await _launch(tester, prefs, api);
    expect(find.byType(HomeScreen), findsOneWidget);
  });

  testWidgets('long press on the wordmark toggles the demo Replay', (tester) async {
    await prefs.setBool('intro_seen', true);
    await _launch(tester, prefs, FakeApi());
    expect(find.text('Replay'), findsNothing);
    await tester.longPress(find.text('NIMBUS'));
    await tester.pump();
    expect(prefs.getString('run_id'), 'replay-michaung');
    expect(find.text('Replay'), findsOneWidget);
  });
}
