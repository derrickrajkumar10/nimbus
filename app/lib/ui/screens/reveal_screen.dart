import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../contracts/nimbus.dart';
import '../../data/api_exception.dart';
import '../../domain/depth.dart';
import '../../domain/threshold_story.dart';
import '../../l10n/app_localizations.dart';
import '../../report/report_flow.dart';
import '../icons.dart';
import '../routes.dart';
import '../theme/tide_colors.dart';
import '../widgets/depth_figure.dart';
import '../widgets/pill_button.dart';
import '../widgets/round_button.dart';
import '../widgets/tide_background.dart';
import '../widgets/tide_map.dart';

const _ok = Color(0xFF18A957);
const _no = Color(0xFFE5322D);
const _warn = Color(0xFFFF8A70);

enum _Phase { verifying, revealing, stillChecking, failed, notVerified }

String depthLabel(DepthBand d, AppLocalizations l) => switch (d) {
      DepthBand.DRY => l.dry,
      DepthBand.ANKLE => l.ankleDeep,
      DepthBand.KNEE => l.kneeDeep,
      DepthBand.WAIST => l.waistDeep,
      DepthBand.ABOVE_WAIST => l.aboveWaist,
    };

String hazardName(HazardClass c, AppLocalizations l) => switch (c) {
      HazardClass.OPEN_MANHOLE => l.hazardOpenManhole,
      HazardClass.FALLEN_TREE => l.hazardFallenTree,
      HazardClass.LIVE_WIRE => l.hazardLiveWire,
      HazardClass.STRANDED_VEHICLE => l.hazardStrandedVehicle,
    };

/// The centrepiece: a sent photo becomes a depth on a figure, the vehicles
/// that can pass, any Hazards, and finally the street on the map, with what
/// the Reading taught the Flood Threshold. Each stage has its own
/// controller; with reduced motion it jumps to the final frame.
class RevealScreen extends ConsumerStatefulWidget {
  const RevealScreen({super.key, required this.submission});

  final ReportSubmission submission;

  @override
  ConsumerState<RevealScreen> createState() => _RevealScreenState();
}

class _RevealScreenState extends ConsumerState<RevealScreen> with TickerProviderStateMixin {
  late final _ripple = _controller(1600);
  late final _shrink = _controller(600);
  late final _rise = _controller(1400);
  late final _label = _controller(400);
  late final _vehicles = _controller(900);
  late final _hazards = _controller(600);
  late final _pull = _controller(1500);
  late final _count = _controller(1200);
  late final _rising = CurvedAnimation(parent: _rise, curve: Curves.easeOutCubic);

  var _phase = _Phase.verifying;
  Verified? _verified;
  ApiException? _error;
  StreamSubscription<ReportState>? _sub;

  /// The ripples play at least this long, so the reveal never feels instant.
  late final Future<void> _minWait = Future<void>.delayed(const Duration(milliseconds: 1200));
  var _started = false;

  AnimationController _controller(int ms) => AnimationController(vsync: this, duration: Duration(milliseconds: ms));

  List<AnimationController> get _stages => [_shrink, _rise, _label, _vehicles, _hazards, _pull, _count];

  bool get _still => MediaQuery.disableAnimationsOf(context);

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_started) return;
    _started = true;
    if (_still) {
      _shrink.value = 1;
    } else {
      _shrink.forward();
      _ripple.repeat();
    }
    _sub = widget.submission.states.listen(_onState, onDone: () {
      if (mounted && _phase == _Phase.verifying) setState(() => _phase = _Phase.notVerified);
    });
  }

  Future<void> _onState(ReportState s) async {
    switch (s) {
      case Verified():
        if (_phase == _Phase.revealing) return;
        if (!_still) await _minWait;
        if (mounted) _play(s);
      case StillChecking():
        if (_phase == _Phase.verifying) {
          _ripple.stop();
          setState(() => _phase = _Phase.stillChecking);
        }
      case Failed(:final e):
        _ripple.stop();
        setState(() {
          _phase = _Phase.failed;
          _error = e;
        });
      case Uploading() || Verifying():
        break;
    }
  }

  Future<void> _play(Verified v) async {
    _ripple.stop();
    setState(() {
      _phase = _Phase.revealing;
      _verified = v;
    });
    if (_still) {
      for (final c in _stages) {
        c.value = 1;
      }
      return;
    }
    await _rise.forward();
    _label.forward();
    await _vehicles.forward();
    if (v.reading.hazardsSeen?.isNotEmpty ?? false) await _hazards.forward();
    await _pull.forward();
    await _count.forward();
  }

  @override
  void dispose() {
    _sub?.cancel();
    _rising.dispose();
    _ripple.dispose();
    for (final c in _stages) {
      c.dispose();
    }
    super.dispose();
  }

  void _home() => Navigator.of(context).popUntil((r) => r.isFirst);

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final v = _verified;
    final calm = switch (_phase) {
      _Phase.stillChecking => (l.stillCheckingTitle, l.stillCheckingBody),
      _Phase.notVerified => (null, l.notVerifiedBody),
      _Phase.failed => (
          null,
          switch (_error?.code) {
            ApiException.runNotStarted => l.replayNotStarted,
            ApiException.photoNotUploaded => l.photoNotUploaded,
            _ => l.reportFailed,
          }
        ),
      _ => null,
    };

    return Scaffold(
      body: TideBackground(
        layerTops: const [0.58, 0.64, 0.72, 0.82, 0.92],
        colors: const [Color(0xFF2E6E99), Color(0xFF225A86), Color(0xFF174775), Color(0xFF0F3561), Color(0xFF0A2849)],
        child: SafeArea(
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Row(children: [
              Padding(
                padding: const EdgeInsets.all(12),
                child: RoundButton(
                  size: 40,
                  color: TideColors.deep,
                  onTap: _home,
                  child: nimbusIcon(NimbusIcon.back, size: 20),
                ),
              ),
              Expanded(
                child: Text(l.yourReport,
                    textAlign: TextAlign.center,
                    style: const TextStyle(fontSize: 11, letterSpacing: 2.6, fontWeight: FontWeight.w600)),
              ),
              const SizedBox(width: 64),
            ]),
            if (v != null)
              FadeTransition(
                opacity: _label,
                child: Center(
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: TideColors.text.withValues(alpha: 0.14),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      l.verifiedChip(v.reading.reportIds.length, (v.reading.confidence * 100).round()),
                      style: const TextStyle(fontSize: 11.5),
                    ),
                  ),
                ),
              ),
            Expanded(child: _stage(v)),
            if (calm != null)
              _Calm(
                title: calm.$1,
                body: calm.$2,
                onRetry: () => Navigator.of(context).pushReplacementNamed(Routes.report),
                onHome: _home,
              )
            else if (v != null)
              _Findings(
                v: v,
                label: _label,
                vehicles: _vehicles,
                hazards: _hazards,
                count: _count,
              )
            else
              Padding(
                padding: const EdgeInsets.only(bottom: 120),
                child: Text(l.verifying, textAlign: TextAlign.center, style: const TextStyle(fontSize: 18)),
              ),
          ]),
        ),
      ),
    );
  }

  /// The upper card: the photo in its frame with ripples, then the figure,
  /// then (under a fading cover) the map.
  Widget _stage(Verified? v) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 10, 16, 10),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(22),
          child: Stack(fit: StackFit.expand, children: [
            if (v != null)
              TideMap(
                segments: [v.segment],
                risk: {v.segment.segmentId: ?v.risk},
                hazards: v.hazards,
                focus: _middle(v.segment.geometry),
                zoom: 16.5,
                waterMarks: [_middle(v.segment.geometry)],
                interactive: false,
              ),
            AnimatedBuilder(
              animation: Listenable.merge([_pull, _rise, _shrink, _ripple]),
              builder: (context, _) => Opacity(
                opacity: 1 - _pull.value,
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: v == null
                        ? null
                        : const LinearGradient(
                            begin: Alignment.topCenter,
                            end: Alignment.bottomCenter,
                            colors: [TideColors.sky0, TideColors.sky1],
                          ),
                  ),
                  child: LayoutBuilder(builder: (context, box) => _frameAndFigure(v, box)),
                ),
              ),
            ),
          ]),
        ),
      );

  Widget _frameAndFigure(Verified? v, BoxConstraints box) {
    final full = math.min(box.maxWidth, box.maxHeight);
    final shrink = Curves.easeInOut.transform(_shrink.value);
    final moved = _rising.value;
    // Full size → a 150 px frame while verifying → a 72 px corner thumbnail.
    final frame = _lerp(_lerp(full, 150, shrink), 72, moved);
    final align = Alignment.lerp(Alignment.center, const Alignment(0.92, -0.9), moved)!;
    final photo = SizedBox.square(
      dimension: frame,
      child: DecoratedBox(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(_lerp(0, 18, shrink)),
          border: Border.all(color: TideColors.text.withValues(alpha: 0.8 * shrink), width: 2),
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(_lerp(0, 16, shrink)),
          child: Image.memory(widget.submission.photo, fit: BoxFit.cover, gaplessPlayback: true),
        ),
      ),
    );
    return Stack(fit: StackFit.expand, children: [
      if (_phase == _Phase.verifying && _ripple.isAnimating)
        CustomPaint(painter: _RipplePainter(_ripple.value, from: frame / 2)),
      if (v != null)
        Opacity(
          opacity: math.min(1, moved * 3),
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 12),
            child: Center(child: DepthFigure(waterFraction: waterFraction(v.reading.depth), progress: _rising)),
          ),
        ),
      Align(alignment: align, child: photo),
    ]);
  }
}

double _lerp(double a, double b, double t) => a + (b - a) * t;

GeoPoint _middle(LineString line) {
  final c = line.coordinates[line.coordinates.length ~/ 2];
  return GeoPoint(lat: c[1], lon: c[0]);
}

/// Three rings spreading from the frame's edge.
class _RipplePainter extends CustomPainter {
  _RipplePainter(this.t, {required this.from});

  final double t;
  final double from;

  @override
  void paint(Canvas canvas, Size size) {
    final centre = size.center(Offset.zero);
    final reach = size.shortestSide / 2;
    for (var i = 0; i < 3; i++) {
      final p = (t + i / 3) % 1;
      canvas.drawCircle(
        centre,
        from + (reach - from) * p,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2
          ..color = TideColors.accent.withValues(alpha: 0.55 * (1 - p)),
      );
    }
  }

  @override
  bool shouldRepaint(_RipplePainter old) => old.t != t || old.from != from;
}

/// Under the card: the depth in both languages, the vehicles, Hazards, and
/// what the Reading did to the Flood Threshold.
class _Findings extends StatelessWidget {
  const _Findings({
    required this.v,
    required this.label,
    required this.vehicles,
    required this.hazards,
    required this.count,
  });

  final Verified v;
  final Animation<double> label;
  final Animation<double> vehicles;
  final Animation<double> hazards;
  final Animation<double> count;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final other = lookupAppLocalizations(Locale(l.localeName == 'ta' ? 'en' : 'ta'));
    final p = v.reading.passable;
    final seen = v.reading.hazardsSeen ?? const <HazardClass>[];

    return Padding(
      padding: const EdgeInsets.fromLTRB(18, 0, 18, 18),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        FadeTransition(
          opacity: label,
          child: Column(children: [
            Text(depthLabel(v.reading.depth, l),
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 36, fontWeight: FontWeight.w600, height: 1.05)),
            const SizedBox(height: 4),
            Text(depthLabel(v.reading.depth, other),
                textAlign: TextAlign.center, style: TextStyle(fontSize: 13, color: TideColors.text.withValues(alpha: 0.85))),
          ]),
        ),
        const SizedBox(height: 14),
        Row(children: [
          for (final (i, icon, name, ok) in [
            (0, NimbusIcon.bike, l.bike, p.twoWheeler),
            (1, NimbusIcon.car, l.car, p.car),
            (2, NimbusIcon.ambulance, l.ambulance, p.ambulance),
          ])
            Expanded(child: _Vehicle(progress: vehicles, index: i, icon: icon, name: name, ok: ok)),
        ]),
        for (final c in seen)
          Padding(
            padding: const EdgeInsets.only(top: 12),
            child: Row(children: [
              AnimatedBuilder(
                animation: hazards,
                // Two pulses over the stage.
                builder: (_, child) =>
                    Transform.scale(scale: 1 + 0.3 * math.sin(2 * math.pi * hazards.value).abs(), child: child),
                child: nimbusIcon(NimbusIcon.warn, size: 20, color: _warn),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(l.hazardHere(hazardName(c, l), _radius(c)), style: const TextStyle(fontSize: 13)),
              ),
            ]),
          ),
        const SizedBox(height: 14),
        AnimatedBuilder(animation: count, builder: (context, _) => _threshold(l)),
      ]),
    );
  }

  int _radius(HazardClass c) =>
      (v.hazards.where((h) => h.hazardClass == c).firstOrNull?.noGoRadiusM ?? 30).round();

  Widget _threshold(AppLocalizations l) {
    final risk = v.risk;
    final story = risk == null ? null : thresholdStory(v.segment, risk);
    final shown = count.value > 0 || count.isCompleted;
    if (story == null || !story.learned) {
      return Opacity(
        opacity: shown ? 1 : 0,
        child: Text(l.confirmedPrediction, style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w600)),
      );
    }
    final mm = _lerp(story.from, story.to, Curves.easeOut.transform(count.value)).round();
    return Opacity(
      opacity: shown ? 1 : 0,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(l.taughtTheMap, style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w600, color: TideColors.accent)),
        Text(l.thresholdNow(v.segment.streetName ?? '', mm, story.from.round()),
            style: const TextStyle(fontSize: 13, color: TideColors.muted)),
      ]),
    );
  }
}

class _Vehicle extends StatelessWidget {
  const _Vehicle({required this.progress, required this.index, required this.icon, required this.name, required this.ok});

  final Animation<double> progress;
  final int index;
  final NimbusIcon icon;
  final String name;
  final bool ok;

  @override
  Widget build(BuildContext context) {
    // 250 ms apart, each falling in over 400 ms.
    final start = index * 250 / 900;
    final t = CurvedAnimation(parent: progress, curve: Interval(start, start + 400 / 900, curve: Curves.easeOutBack));
    return AnimatedBuilder(
      animation: progress,
      builder: (context, child) => Opacity(
        opacity: t.value.clamp(0.0, 1.0),
        child: Transform.translate(offset: Offset(0, -24 * (1 - t.value)), child: child),
      ),
      child: Column(children: [
        SizedBox.square(
          dimension: 48,
          child: Stack(clipBehavior: Clip.none, children: [
            Container(
              decoration: BoxDecoration(color: TideColors.text.withValues(alpha: 0.12), shape: BoxShape.circle),
              alignment: Alignment.center,
              child: nimbusIcon(icon, size: 21),
            ),
            Positioned(
              right: -3,
              bottom: -3,
              child: Container(
                key: ValueKey(ok ? 'pass-ok' : 'pass-no'),
                width: 20,
                height: 20,
                decoration: BoxDecoration(
                  color: ok ? _ok : _no,
                  shape: BoxShape.circle,
                  border: Border.all(color: TideColors.text, width: 2),
                ),
                alignment: Alignment.center,
                child: nimbusIcon(ok ? NimbusIcon.check : NimbusIcon.x, size: 11),
              ),
            ),
          ]),
        ),
        const SizedBox(height: 6),
        Text(name, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600)),
      ]),
    );
  }
}

class _Calm extends StatelessWidget {
  const _Calm({this.title, required this.body, required this.onRetry, required this.onHome});

  final String? title;
  final String body;
  final VoidCallback onRetry;
  final VoidCallback onHome;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(28, 0, 28, 20),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        if (title != null)
          Text(title!, textAlign: TextAlign.center, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w600)),
        const SizedBox(height: 8),
        Text(body, textAlign: TextAlign.center, style: const TextStyle(fontSize: 15, color: TideColors.muted, height: 1.35)),
        const SizedBox(height: 22),
        PillButton(label: l.home, onTap: onHome),
        PillButton(label: l.tryAgain, quiet: true, onTap: onRetry),
      ]),
    );
  }
}
