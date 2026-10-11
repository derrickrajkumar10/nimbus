import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'app.dart';
import 'data/install_id.dart';
import 'push/push_service.dart';
import 'state/providers.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final prefs = await SharedPreferences.getInstance();
  final installId = await loadInstallId(prefs);
  // Without google-services.json there's no Firebase app: run with push off.
  var firebaseReady = false;
  try {
    await Firebase.initializeApp();
    firebaseReady = true;
  } catch (e) {
    debugPrint('Firebase not configured, push is off: $e');
  }
  runApp(ProviderScope(
    overrides: [
      prefsProvider.overrideWithValue(prefs),
      installIdProvider.overrideWithValue(installId),
      firebaseReadyProvider.overrideWithValue(firebaseReady),
      notificationPermissionProvider
          .overrideWith((ref) => () async => ref.read(firebasePlatformProvider)?.requestPermission()),
    ],
    child: const NimbusApp(),
  ));
}
