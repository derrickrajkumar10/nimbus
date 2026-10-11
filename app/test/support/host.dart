import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nimbus_app/l10n/app_localizations.dart';
import 'package:nimbus_app/state/providers.dart';
import 'package:nimbus_app/ui/routes.dart';
import 'package:nimbus_app/ui/theme/tide_theme.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'fake_api.dart';
import 'fixtures.dart';

/// Pumps [screen] in the app's theme, localisations and routes, on a fake
/// API. [risk] replaces polling with one fixed snapshot.
Future<SharedPreferences> pumpScreen(
  WidgetTester tester,
  Widget screen, {
  FakeApi? api,
  RiskSnapshot? risk,
  String lang = 'en',
  String runId = demoRun,
  Map<String, Object> prefs = const {},
  List<dynamic> overrides = const [],
}) async {
  SharedPreferences.setMockInitialValues({'lang': lang, 'run_id': runId, 'intro_seen': true, ...prefs});
  final p = await SharedPreferences.getInstance();
  final locale = Locale(lang);
  await tester.pumpWidget(ProviderScope(
    overrides: [
      prefsProvider.overrideWithValue(p),
      apiProvider.overrideWithValue(api ?? FakeApi()),
      notificationPermissionProvider.overrideWithValue(() async {}),
      if (risk != null) riskProvider.overrideWith((ref) => Stream.value(risk)),
      ...overrides.cast(),
    ],
    child: MaterialApp(
      locale: locale,
      supportedLocales: AppLocalizations.supportedLocales,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      theme: tideTheme(locale),
      home: screen,
      onGenerateRoute: generateRoute,
    ),
  ));
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 50));
  return p;
}

/// The fixture risk as one fresh snapshot.
RiskSnapshot fixtureSnapshot({bool stale = false}) {
  final s = RiskSnapshot.of(fixtureRisk().values.toList());
  return stale ? s.asStale() : s;
}
