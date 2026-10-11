import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../theme/tide_colors.dart';

/// Layer tops on Home, as in the Deep tide mockup (waves from 186 px of a
/// 580 px phone, 66 px apart).
const homeLayerTops = [0.32, 0.434, 0.548, 0.662, 0.776, 0.89];

/// [n] wave colours from the lightest to the deepest Deep tide shade.
List<Color> tideShades(int n) {
  const w = TideColors.waves;
  if (n <= 1) return [w.first];
  return [
    for (var i = 0; i < n; i++)
      () {
        final t = i / (n - 1) * (w.length - 1);
        final lo = t.floor().clamp(0, w.length - 2);
        return Color.lerp(w[lo], w[lo + 1], t - lo)!;
      }(),
  ];
}

/// The Deep tide sea: a storm-sky gradient, thin rain, and layered waves that
/// drift slowly. Screens lay their content on the layers via [layerRects].
class TideBackground extends StatefulWidget {
  const TideBackground({
    super.key,
    required this.layerTops,
    this.colors = TideColors.waves,
    this.amplitude = 10,
    this.rain = true,
    this.child,
  });

  /// Fractions (0..1) of the height where each layer starts, back to front.
  final List<double> layerTops;
  final List<Color> colors;
  final double amplitude;
  final bool rain;
  final Widget? child;

  static const wavelength = 88.0;
  static const driftPeriod = Duration(seconds: 8);

  /// The top y of each layer for a box of [size].
  static List<double> layerRects(Size size, List<double> layerTops) =>
      [for (final t in layerTops) t * size.height];

  @override
  State<TideBackground> createState() => _TideBackgroundState();
}

class _TideBackgroundState extends State<TideBackground> with SingleTickerProviderStateMixin {
  late final AnimationController _drift =
      AnimationController(vsync: this, duration: TideBackground.driftPeriod);

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final still = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
    if (still) {
      _drift.stop();
    } else if (!_drift.isAnimating) {
      _drift.repeat();
    }
  }

  @override
  void dispose() {
    _drift.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => CustomPaint(
        painter: _TidePainter(
          phase: _drift,
          layerTops: widget.layerTops,
          colors: widget.colors,
          amplitude: widget.amplitude,
          rain: widget.rain,
        ),
        child: widget.child == null ? const SizedBox.expand() : SizedBox.expand(child: widget.child),
      );
}

// Streak positions from the mockup, as fractions of a 268 x 580 phone.
const _streaks = [
  (20.0, 40.0, 16.0), (60.0, 70.0, 12.0), (110.0, 30.0, 18.0), (160.0, 80.0, 14.0),
  (210.0, 44.0, 16.0), (240.0, 96.0, 12.0), (36.0, 120.0, 14.0), (190.0, 130.0, 12.0),
  (88.0, 150.0, 10.0), (140.0, 118.0, 16.0),
];

class _TidePainter extends CustomPainter {
  _TidePainter({
    required this.phase,
    required this.layerTops,
    required this.colors,
    required this.amplitude,
    required this.rain,
  }) : super(repaint: phase);

  final Animation<double> phase;
  final List<double> layerTops;
  final List<Color> colors;
  final double amplitude;
  final bool rain;

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset.zero & size;
    canvas.drawRect(
      rect,
      Paint()
        ..shader = const LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [TideColors.sky0, TideColors.sky1, TideColors.sky2, TideColors.deep],
          stops: [0, 0.3, 0.6, 1],
        ).createShader(rect),
    );
    if (rain) _paintRain(canvas, size);

    const w = TideBackground.wavelength;
    final tops = TideBackground.layerRects(size, layerTops);
    for (var i = 0; i < tops.length; i++) {
      // Alternate layers drift in opposite directions; one wavelength per loop
      // keeps the repeat seamless.
      final t = i.isEven ? phase.value : 1 - phase.value;
      final dx = (t * w + i * 37) % w;
      final top = tops[i];
      final crest = top - amplitude + (i % 2) * 4;
      final trough = top + amplitude - (i % 2) * 4;
      final path = Path()..moveTo(-w + dx, top);
      for (var x = -w + dx; x < size.width + w; x += w) {
        path
          ..quadraticBezierTo(x + 22, crest, x + 44, top)
          ..quadraticBezierTo(x + 66, trough, x + w, top);
      }
      path
        ..lineTo(size.width + w, size.height)
        ..lineTo(-w, size.height)
        ..close();
      canvas.drawPath(path, Paint()..color = colors[i % colors.length]);
    }
  }

  void _paintRain(Canvas canvas, Size size) {
    final sx = size.width / 268, sy = size.height / 580;
    final paint = Paint()
      ..color = Colors.white.withValues(alpha: 0.35)
      ..strokeWidth = 1;
    // Rain falls a little with the drift: 40 px per loop, wrapped to the sky.
    final skyBottom = layerTops.isEmpty ? size.height : layerTops.first * size.height;
    final fall = phase.value * 40 * sy;
    const angle = 14 * math.pi / 180;
    for (final (x, y, l) in _streaks) {
      final top = (y * sy + fall) % math.max(skyBottom, 1);
      final len = l * sy;
      final start = Offset(x * sx, top);
      final end = start + Offset(-math.sin(angle) * len, math.cos(angle) * len);
      canvas.drawLine(start, end, paint);
    }
  }

  @override
  bool shouldRepaint(_TidePainter old) =>
      old.layerTops != layerTops || old.colors != colors || old.amplitude != amplitude || old.rain != rain;
}
