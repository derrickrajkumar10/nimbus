import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../theme/tide_colors.dart';

/// A standing figure (as `body()` in the mockup generator, in a 100 x 220
/// box) behind layered water. The water's top sits at [waterFraction] of the
/// figure's height from the feet, times [progress]. When [progress]
/// completes the water sloshes once: a damped 3 px sine over 600 ms.
/// Dashed lines mark the ankle and the waist.
class DepthFigure extends StatefulWidget {
  const DepthFigure({super.key, required this.waterFraction, required this.progress});

  final double waterFraction;
  final Animation<double> progress;

  static const size = Size(100, 220);

  @override
  State<DepthFigure> createState() => _DepthFigureState();
}

class _DepthFigureState extends State<DepthFigure> with SingleTickerProviderStateMixin {
  late final _slosh = AnimationController(vsync: this, duration: const Duration(milliseconds: 600));

  @override
  void initState() {
    super.initState();
    widget.progress.addStatusListener(_onStatus);
  }

  @override
  void didUpdateWidget(DepthFigure old) {
    super.didUpdateWidget(old);
    if (old.progress != widget.progress) {
      old.progress.removeStatusListener(_onStatus);
      widget.progress.addStatusListener(_onStatus);
    }
  }

  void _onStatus(AnimationStatus s) {
    if (s == AnimationStatus.completed && !MediaQuery.disableAnimationsOf(context)) _slosh.forward(from: 0);
  }

  @override
  void dispose() {
    widget.progress.removeStatusListener(_onStatus);
    _slosh.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AspectRatio(
        aspectRatio: DepthFigure.size.width / DepthFigure.size.height,
        child: CustomPaint(
          painter: _FigurePainter(
            waterFraction: widget.waterFraction,
            progress: widget.progress,
            slosh: _slosh,
          ),
        ),
      );
}

class _FigurePainter extends CustomPainter {
  _FigurePainter({required this.waterFraction, required this.progress, required this.slosh})
      : super(repaint: Listenable.merge([progress, slosh]));

  final double waterFraction;
  final Animation<double> progress;
  final Animation<double> slosh;

  static const _skin = Color(0xFFD3E3EE);
  static const _water = [Color(0x993E78A0), Color(0xB32E6690), Color(0xCC22557F)];

  @override
  void paint(Canvas canvas, Size size) {
    canvas.save();
    canvas.scale(size.width / DepthFigure.size.width, size.height / DepthFigure.size.height);
    const h = 220.0;

    // The figure: head, torso, arms, legs.
    final skin = Paint()..color = _skin;
    canvas.drawCircle(const Offset(50, 20), 14, skin);
    for (final (x, y, w, ht, r) in const [
      (34.0, 38.0, 32.0, 74.0, 13.0),
      (21.0, 42.0, 11.0, 64.0, 5.5),
      (68.0, 42.0, 11.0, 64.0, 5.5),
      (36.0, 104.0, 13.0, 110.0, 6.5),
      (51.0, 104.0, 13.0, 110.0, 6.5),
    ]) {
      canvas.drawRRect(RRect.fromLTRBR(x, y, x + w, y + ht, Radius.circular(r)), skin);
    }

    // The water, in three layers with a gentle wave on top.
    final t = slosh.value;
    final sloshPx = t == 0 || t == 1 ? 0.0 : 3 * math.sin(t * 4 * math.pi) * (1 - t);
    final top = h - waterFraction * h * progress.value + sloshPx;
    if (progress.value > 0) {
      for (var i = 0; i < _water.length; i++) {
        final y = top + i * 5.0;
        final phase = i * 9.0;
        final path = Path()..moveTo(-25, y);
        for (var x = -25.0; x < 125; x += 25) {
          path.quadraticBezierTo(x + 6.25 + phase % 12.5, y - 3, x + 12.5, y);
          path.quadraticBezierTo(x + 18.75, y + 3, x + 25, y);
        }
        path
          ..lineTo(125, h)
          ..lineTo(-25, h)
          ..close();
        canvas.drawPath(path, Paint()..color = _water[i]);
      }
    }

    // Ankle and waist marks.
    final dash = Paint()
      ..color = TideColors.text.withValues(alpha: 0.5)
      ..strokeWidth = 1;
    for (final y in const [200.0, 110.0]) {
      for (var x = 0.0; x < 100; x += 5) {
        canvas.drawLine(Offset(x, y), Offset(x + 2, y), dash);
      }
    }
    canvas.restore();
  }

  @override
  bool shouldRepaint(_FigurePainter old) => old.waterFraction != waterFraction;
}
