import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:video_player/video_player.dart';

import '../../l10n/app_localizations.dart';

const introLogo = 'assets/brand/nimbus_logo.png';
const _introVideo = 'assets/brand/nimbus_intro.mp4';
const _navy = Color(0xFF0B2A5C);

/// Makes the intro's video player. Null shows the still logo instead (tests,
/// where there's no video platform).
final introVideoProvider = Provider<VideoPlayerController? Function()>(
    (ref) => () => VideoPlayerController.asset(_introVideo));

/// The one-time intro: the 4 s NIMBUS logo film on white, then the launch
/// gate cross-fades into the tide. With reduce motion, or if the video can't
/// play, the still logo shows briefly instead.
class IntroScreen extends ConsumerStatefulWidget {
  const IntroScreen({super.key, required this.onDone});

  final VoidCallback onDone;

  /// How long the still logo shows when there's no video.
  static const stillLength = Duration(seconds: 4);

  /// Never hold the user longer than this, even if the video stalls.
  static const maxLength = Duration(seconds: 8);

  @override
  ConsumerState<IntroScreen> createState() => _IntroScreenState();
}

class _IntroScreenState extends ConsumerState<IntroScreen> {
  VideoPlayerController? _video;
  var _playing = false;
  var _started = false;
  var _done = false;
  final _timers = <Timer>[];

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_started) return;
    _started = true;
    final still = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
    final video = still ? null : ref.read(introVideoProvider)();
    if (video == null) {
      _timers.add(Timer(still ? const Duration(seconds: 2) : IntroScreen.stillLength, _finish));
      return;
    }
    _video = video;
    _timers.add(Timer(IntroScreen.maxLength, _finish));
    video.initialize().then((_) {
      if (!mounted) return;
      video.addListener(_onTick);
      setState(() => _playing = true);
      video.play();
    }).catchError((Object _) {
      // No playable video: fall back to the still logo.
      _timers.add(Timer(IntroScreen.stillLength, _finish));
    });
  }

  void _onTick() {
    final v = _video!.value;
    if (v.isCompleted || (v.duration > Duration.zero && v.position >= v.duration)) _finish();
  }

  void _finish() {
    if (_done) return;
    _done = true;
    _video?.pause();
    widget.onDone();
  }

  @override
  void dispose() {
    for (final t in _timers) {
      t.cancel();
    }
    _video?.removeListener(_onTick);
    _video?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final video = _video;
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.dark,
      child: Scaffold(
        backgroundColor: Colors.white,
        body: Stack(children: [
          Center(
            child: _playing && video != null
                ? FittedBox(
                    fit: BoxFit.contain,
                    child: SizedBox(
                      width: video.value.size.width,
                      height: video.value.size.height,
                      child: Semantics(label: 'NIMBUS', image: true, child: VideoPlayer(video)),
                    ),
                  )
                : FractionallySizedBox(
                    widthFactor: 0.62,
                    child: Image.asset(introLogo, semanticLabel: 'NIMBUS', fit: BoxFit.contain),
                  ),
          ),
          SafeArea(
            child: Align(
              alignment: Alignment.topRight,
              child: TextButton(
                onPressed: _finish,
                style: TextButton.styleFrom(foregroundColor: _navy),
                child: Text(AppLocalizations.of(context).skip),
              ),
            ),
          ),
        ]),
      ),
    );
  }
}
