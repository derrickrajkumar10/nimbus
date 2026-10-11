import 'package:flutter/material.dart';

import '../theme/tide_colors.dart';

/// A round Deep tide control with a soft 6 px halo and an optional label.
class RoundButton extends StatelessWidget {
  const RoundButton({
    super.key,
    required this.child,
    required this.onTap,
    this.label,
    this.color = TideColors.button,
    this.size = 48,
  });

  final Widget child;
  final VoidCallback onTap;
  final String? label;
  final Color color;
  final double size;

  @override
  Widget build(BuildContext context) {
    final button = Semantics(
      button: true,
      label: label,
      child: GestureDetector(
        onTap: onTap,
        behavior: HitTestBehavior.opaque,
        child: Container(
          width: size,
          height: size,
          margin: const EdgeInsets.all(6),
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: color,
            shape: BoxShape.circle,
            boxShadow: [BoxShadow(color: color.withValues(alpha: 0.16), spreadRadius: 6)],
          ),
          child: child,
        ),
      ),
    );
    if (label == null) return button;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        button,
        const SizedBox(height: 1),
        Text(label!, style: const TextStyle(fontSize: 10.5, color: TideColors.muted)),
      ],
    );
  }
}
