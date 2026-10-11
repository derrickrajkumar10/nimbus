import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'l10n/app_localizations.dart';
import 'state/providers.dart';
import 'ui/routes.dart';
import 'ui/theme/tide_theme.dart';

final rootNavigatorKey = GlobalKey<NavigatorState>();

class NimbusApp extends ConsumerWidget {
  const NimbusApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final locale = ref.watch(localeProvider);
    return MaterialApp(
      title: 'NIMBUS',
      debugShowCheckedModeBanner: false,
      navigatorKey: rootNavigatorKey,
      locale: locale,
      supportedLocales: AppLocalizations.supportedLocales,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      theme: tideTheme(locale),
      initialRoute: Routes.launch,
      onGenerateRoute: generateRoute,
    );
  }
}
