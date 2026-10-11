import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'app.dart';
import 'data/install_id.dart';
import 'state/providers.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final prefs = await SharedPreferences.getInstance();
  final installId = await loadInstallId(prefs);
  runApp(ProviderScope(
    overrides: [
      prefsProvider.overrideWithValue(prefs),
      installIdProvider.overrideWithValue(installId),
    ],
    child: const NimbusApp(),
  ));
}
