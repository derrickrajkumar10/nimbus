import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../l10n/app_localizations.dart';
import '../../state/providers.dart';
import '../theme/tide_colors.dart';

/// "NIMBUS", spaced out. A long press toggles the hidden demo Run
/// (`replay-michaung`), shown by a small "Replay" tag.
class Wordmark extends ConsumerWidget {
  const Wordmark({super.key, this.fontSize = 12});

  final double fontSize;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final demo = ref.watch(runIdProvider) == demoRun;
    return GestureDetector(
      onLongPress: () => ref.read(runIdProvider.notifier).toggleDemo(),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('NIMBUS',
              style: TextStyle(
                fontFamily: 'Outfit',
                fontSize: fontSize,
                fontWeight: FontWeight.w600,
                letterSpacing: fontSize * 0.32,
                color: TideColors.text,
              )),
          if (demo) ...[
            const SizedBox(width: 6),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
              decoration: BoxDecoration(
                color: TideColors.sos.withValues(alpha: 0.22),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Text(AppLocalizations.of(context).replayTag,
                  style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: TideColors.text)),
            ),
          ],
        ],
      ),
    );
  }
}
