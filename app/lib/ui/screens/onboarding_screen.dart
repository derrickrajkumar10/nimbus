import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../l10n/app_localizations.dart';
import '../../state/providers.dart';
import '../routes.dart';
import '../theme/tide_colors.dart';
import '../widgets/pill_button.dart';
import '../widgets/tide_background.dart';
import '../widgets/wordmark.dart';

/// First run, in three steps on the tide: language, notifications, and the
/// first place. Saving that place takes the launch gate to Home.
class OnboardingScreen extends ConsumerStatefulWidget {
  const OnboardingScreen({super.key});

  @override
  ConsumerState<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends ConsumerState<OnboardingScreen> {
  var _step = 0;

  void _language(String code) {
    ref.read(languageProvider.notifier).set(code);
    setState(() => _step = 1);
  }

  Future<void> _allow() async {
    await ref.read(notificationPermissionProvider)();
    if (mounted) setState(() => _step = 2);
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final step = switch (_step) {
      0 => _Step(key: const ValueKey(0), title: l.chooseLanguage, actions: [
          PillButton(label: 'தமிழ்', onTap: () => _language('ta')),
          const SizedBox(height: 12),
          PillButton(label: 'English', onTap: () => _language('en')),
        ]),
      1 => _Step(key: const ValueKey(1), title: l.allowAlertsTitle, body: l.allowAlertsBody, actions: [
          PillButton(label: l.allowAlerts, onTap: _allow),
          PillButton(label: l.notNow, quiet: true, onTap: () => setState(() => _step = 2)),
        ]),
      _ => _Step(key: const ValueKey(2), title: l.addFirstPlaceTitle, body: l.addFirstPlaceBody, actions: [
          PillButton(label: l.addPlace, onTap: () => Navigator.of(context).pushNamed(Routes.placeEdit)),
        ]),
    };
    return Scaffold(
      body: TideBackground(
        layerTops: const [0.70, 0.76, 0.82, 0.88, 0.94],
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(28, 12, 28, 24),
            child: Column(
              children: [
                const Wordmark(),
                const Spacer(),
                AnimatedSwitcher(duration: const Duration(milliseconds: 350), child: step),
                const SizedBox(height: 8),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _Step extends StatelessWidget {
  const _Step({super.key, required this.title, this.body, required this.actions});

  final String title;
  final String? body;
  final List<Widget> actions;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(title,
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w500, height: 1.2)),
          if (body != null) ...[
            const SizedBox(height: 10),
            Text(body!, textAlign: TextAlign.center, style: const TextStyle(fontSize: 15, color: TideColors.muted)),
          ],
          const SizedBox(height: 28),
          ...actions,
        ],
      );
}
