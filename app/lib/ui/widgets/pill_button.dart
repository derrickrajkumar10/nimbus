import 'package:flutter/material.dart';

import '../theme/tide_colors.dart';

/// A full-width teal pill for a screen's main action.
class PillButton extends StatelessWidget {
  const PillButton({super.key, required this.label, required this.onTap, this.color = TideColors.button, this.quiet = false});

  final String label;
  final VoidCallback? onTap;
  final Color color;

  /// A secondary action: text only.
  final bool quiet;

  @override
  Widget build(BuildContext context) {
    final text = Text(label, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: TideColors.text));
    if (quiet) {
      return TextButton(
        onPressed: onTap,
        style: TextButton.styleFrom(foregroundColor: TideColors.muted, minimumSize: const Size.fromHeight(48)),
        child: DefaultTextStyle.merge(style: const TextStyle(color: TideColors.muted), child: Text(label)),
      );
    }
    return Semantics(
      button: true,
      child: Material(
        color: onTap == null ? color.withValues(alpha: 0.4) : color,
        shape: const StadiumBorder(),
        child: InkWell(
          onTap: onTap,
          customBorder: const StadiumBorder(),
          child: SizedBox(height: 52, child: Center(child: text)),
        ),
      ),
    );
  }
}
