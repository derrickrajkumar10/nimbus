import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../state/providers.dart';
import '../widgets/tide_background.dart';
import 'home_screen.dart';
import 'intro_screen.dart';
import 'onboarding_screen.dart';

/// The first screen: the intro once, then first run until a place exists,
/// then Home.
class LaunchGate extends ConsumerWidget {
  const LaunchGate({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final Widget child;
    if (!ref.watch(introSeenProvider)) {
      child = IntroScreen(
        key: const ValueKey('intro'),
        onDone: () async {
          await ref.read(prefsProvider).setBool('intro_seen', true);
          ref.invalidate(introSeenProvider);
        },
      );
    } else {
      child = switch (ref.watch(placesProvider)) {
        AsyncData(:final value) when value.isEmpty => const OnboardingScreen(key: ValueKey('onboarding')),
        AsyncData() || AsyncError() => const HomeScreen(key: ValueKey('home')),
        _ => const TideBackground(key: ValueKey('loading'), layerTops: homeLayerTops),
      };
    }
    return AnimatedSwitcher(duration: const Duration(milliseconds: 400), child: child);
  }
}
