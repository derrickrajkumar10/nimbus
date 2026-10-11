import 'package:flutter/material.dart';

import 'screens/home_screen.dart';
import 'screens/launch_gate.dart';
import 'screens/onboarding_screen.dart';
import 'theme/tide_colors.dart';

/// Route names. `/place/:id` carries the place id in the path.
abstract final class Routes {
  static const launch = '/';
  static const intro = '/intro';
  static const onboarding = '/onboarding';
  static const home = '/home';
  static const placeEdit = '/place/edit';
  static const map = '/map';
  static const report = '/report';
  static const reveal = '/reveal';
  static const route = '/route';
  static const sos = '/sos';

  static String place(String id) => '/place/${Uri.encodeComponent(id)}';
}

Route<dynamic> generateRoute(RouteSettings settings) {
  final name = settings.name ?? Routes.launch;
  Widget page;
  switch (name) {
    case Routes.launch:
    case Routes.intro:
      page = const LaunchGate();
    case Routes.onboarding:
      page = const OnboardingScreen();
    case Routes.home:
      page = const HomeScreen();
    default:
      page = _NotBuiltYet(name);
  }
  return MaterialPageRoute(settings: settings, builder: (_) => page);
}

/// Screens later tasks add. Never reached in a finished build.
class _NotBuiltYet extends StatelessWidget {
  const _NotBuiltYet(this.name);
  final String name;

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(backgroundColor: TideColors.deep),
        body: Center(child: Text(name, style: const TextStyle(color: TideColors.muted))),
      );
}
