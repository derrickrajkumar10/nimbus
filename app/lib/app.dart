import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'l10n/app_localizations.dart';
import 'push/push_service.dart';
import 'state/providers.dart';
import 'ui/routes.dart';
import 'ui/theme/tide_theme.dart';

final rootNavigatorKey = GlobalKey<NavigatorState>();

class NimbusApp extends ConsumerStatefulWidget {
  const NimbusApp({super.key});

  @override
  ConsumerState<NimbusApp> createState() => _NimbusAppState();
}

class _NimbusAppState extends ConsumerState<NimbusApp> {
  @override
  void initState() {
    super.initState();
    // After the first frame, so a push that launched the app can navigate.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) ref.read(pushServiceProvider)?.start(ref.read(languageProvider));
    });
  }

  @override
  Widget build(BuildContext context) {
    ref.listen(languageProvider, (_, lang) => ref.read(pushServiceProvider)?.setLanguage(lang));
    final locale = ref.watch(localeProvider);
    return MaterialApp(
      title: 'NIMBUS',
      debugShowCheckedModeBanner: false,
      navigatorKey: rootNavigatorKey,
      locale: locale,
      supportedLocales: AppLocalizations.supportedLocales,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      theme: tideTheme(locale),
      // `flutter run --route /map` (or a deep link) opens on that screen.
      initialRoute: WidgetsBinding.instance.platformDispatcher.defaultRouteName,
      onGenerateRoute: generateRoute,
    );
  }
}
