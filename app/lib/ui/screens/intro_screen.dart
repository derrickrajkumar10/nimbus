import 'dart:async';

import 'package:flutter/material.dart';

import '../../l10n/app_localizations.dart';
import '../theme/tide_colors.dart';
import '../widgets/tide_background.dart';

/// The one-time intro, about 6 s: rain falls, the tide rises to the Home
/// layers, then the wordmark and the tagline in English and Tamil.
class IntroScreen extends StatefulWidget {
  const IntroScreen({super.key, required this.onDone});

  final VoidCallback onDone;

  static const length = Duration(seconds: 6);

  @override
  State<IntroScreen> createState() => _IntroScreenState();
}

class _IntroScreenState extends State<IntroScreen> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this, duration: IntroScreen.length)
    ..addStatusListener((s) {
      if (s == AnimationStatus.completed) _finish();
    });
  Timer? _still;
  var _done = false;

  late final Animation<double> _tide =
      CurvedAnimation(parent: _c, curve: const Interval(1.5 / 6, 3.5 / 6, curve: Curves.easeInOutCubic));
  late final Animation<double> _mark =
      CurvedAnimation(parent: _c, curve: const Interval(3.5 / 6, 5 / 6, curve: Curves.easeOut));
  late final Animation<double> _tagline =
      CurvedAnimation(parent: _c, curve: const Interval(5 / 6, 1, curve: Curves.easeOut));

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_c.isAnimating || _c.isCompleted || _still != null) return;
    if (MediaQuery.maybeDisableAnimationsOf(context) ?? false) {
      // Reduce motion: show the final frame, then move on.
      _c.value = 1;
      _still = Timer(const Duration(seconds: 2), _finish);
    } else {
      _c.forward();
    }
  }

  void _finish() {
    if (_done) return;
    _done = true;
    widget.onDone();
  }

  @override
  void dispose() {
    _still?.cancel();
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        body: AnimatedBuilder(
          animation: _c,
          builder: (context, _) => TideBackground(
            layerTops: [for (final t in homeLayerTops) 1.0 + (t - 1.0) * _tide.value],
            child: Stack(
              children: [
                Align(
                  alignment: const Alignment(0, -0.42),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Opacity(
                        opacity: _mark.value,
                        child: const Text('NIMBUS',
                            style: TextStyle(
                              fontFamily: 'Outfit',
                              fontSize: 34,
                              fontWeight: FontWeight.w600,
                              letterSpacing: 34 * 0.32,
                              color: TideColors.text,
                            )),
                      ),
                      const SizedBox(height: 14),
                      Opacity(
                        opacity: _tagline.value,
                        child: const Column(children: [
                          // Both languages, whatever the app language.
                          Text('Know before the water does',
                              style: TextStyle(fontFamily: 'Outfit', fontSize: 16, color: TideColors.text)),
                          SizedBox(height: 4),
                          Text('நீர் வரும் முன் அறிந்திடுங்கள்',
                              style: TextStyle(fontFamily: 'NotoSansTamil', fontSize: 13, color: TideColors.muted)),
                        ]),
                      ),
                    ],
                  ),
                ),
                SafeArea(
                  child: Align(
                    alignment: Alignment.topRight,
                    child: TextButton(
                      onPressed: _finish,
                      style: TextButton.styleFrom(foregroundColor: TideColors.text),
                      child: Text(AppLocalizations.of(context).skip),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      );
}
