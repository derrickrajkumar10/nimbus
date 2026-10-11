import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_image_compress/flutter_image_compress.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../contracts/nimbus.dart';
import '../../data/api_exception.dart';
import '../../l10n/app_localizations.dart';
import '../../report/report_flow.dart';
import '../../state/providers.dart';
import '../icons.dart';
import '../routes.dart';
import '../theme/tide_colors.dart';
import '../widgets/pill_button.dart';
import '../widgets/round_button.dart';
import '../widgets/tide_background.dart';
import '../widgets/tide_map.dart';

const _longEdge = 1600.0;
const _quality = 80;

bool _isJpeg(Uint8List b) => b.length > 2 && b[0] == 0xFF && b[1] == 0xD8;

/// Takes or picks a photo, at most 1600 px on the long edge, as JPEG at
/// quality 80. Null when the user backs out.
Future<Uint8List?> pickReportPhoto(ImageSource source) async {
  final file = await ImagePicker()
      .pickImage(source: source, maxWidth: _longEdge, maxHeight: _longEdge, imageQuality: _quality);
  if (file == null) return null;
  final bytes = await file.readAsBytes();
  // The camera gives JPEG already; a gallery PNG or HEIC is converted.
  if (_isJpeg(bytes)) return bytes;
  return FlutterImageCompress.compressWithList(bytes,
      minWidth: _longEdge.toInt(), minHeight: _longEdge.toInt(), quality: _quality, format: CompressFormat.jpeg);
}

/// Replaced in tests.
final photoPickerProvider = Provider<Future<Uint8List?> Function(ImageSource)>((ref) => pickReportPhoto);

/// A photo Report: the photo, where it was taken, then send. In `live` the
/// location is GPS. In a Replay the demo phones aren't in Velachery, so it's
/// a pin that starts on [placeId] (or the first Saved Place).
class ReportScreen extends ConsumerStatefulWidget {
  const ReportScreen({super.key, this.placeId});

  final String? placeId;

  @override
  ConsumerState<ReportScreen> createState() => _ReportScreenState();
}

class _ReportScreenState extends ConsumerState<ReportScreen> {
  Uint8List? _photo;
  GeoPoint? _pin;
  ReportState? _state;
  StreamSubscription<ReportState>? _sub;
  var _handedOff = false;

  bool get _sending => _state is Uploading;

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }

  Future<void> _pick(ImageSource source) async {
    final photo = await ref.read(photoPickerProvider)(source);
    if (photo != null && mounted) {
      setState(() {
        _photo = photo;
        _state = null;
      });
    }
  }

  void _send(GeoPoint location) {
    final photo = _photo!;
    // Polling stops once nobody listens. This screen listens until it's
    // disposed, by which time the reveal has taken over the stream.
    final states = ReportFlow(ref.read(apiProvider), ref.read(runIdProvider))
        .submit(photo, location)
        .asBroadcastStream(onCancel: (sub) => sub.cancel());
    _sub?.cancel();
    _sub = states.listen((s) {
      if (!mounted || _handedOff) return;
      if (s is Verifying) {
        _handedOff = true;
        Navigator.of(context).pushReplacementNamed(Routes.reveal,
            arguments: ReportSubmission(photo: photo, reportId: s.reportId, states: states));
        return;
      }
      setState(() => _state = s);
    });
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final failed = _state is Failed ? (_state as Failed).e : null;
    final Widget body;
    if (failed != null) {
      body = _FailedPanel(e: failed, onRetry: () => setState(() => _state = null));
    } else if (_photo == null) {
      body = _Intro(onCamera: () => _pick(ImageSource.camera), onGallery: () => _pick(ImageSource.gallery));
    } else {
      body = _Confirm(
        photo: _photo!,
        sending: _sending,
        replay: ref.watch(runIdProvider) != liveRun,
        placeId: widget.placeId,
        pin: _pin,
        onPin: (p) => _pin = p,
        onRetake: () => _pick(ImageSource.camera),
        onSend: _send,
      );
    }
    return Scaffold(
      body: TideBackground(
        layerTops: const [0.80, 0.85, 0.90, 0.95],
        child: SafeArea(
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Row(children: [
              Padding(
                padding: const EdgeInsets.all(12),
                child: RoundButton(
                  size: 40,
                  color: TideColors.deep,
                  onTap: () => Navigator.of(context).maybePop(),
                  child: nimbusIcon(NimbusIcon.back, size: 20),
                ),
              ),
              Text(l.reportTitle, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w600)),
            ]),
            Expanded(child: body),
          ]),
        ),
      ),
    );
  }
}

class _Intro extends StatelessWidget {
  const _Intro({required this.onCamera, required this.onGallery});

  final VoidCallback onCamera;
  final VoidCallback onGallery;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(28, 0, 28, 24),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        const Spacer(),
        Center(child: nimbusIcon(NimbusIcon.camera, size: 56, color: TideColors.accent)),
        const SizedBox(height: 18),
        Text(l.reportBody,
            textAlign: TextAlign.center, style: const TextStyle(fontSize: 16, color: TideColors.muted, height: 1.35)),
        const Spacer(),
        PillButton(label: l.takePhoto, onTap: onCamera),
        PillButton(label: l.choosePhoto, quiet: true, onTap: onGallery),
      ]),
    );
  }
}

class _Confirm extends ConsumerWidget {
  const _Confirm({
    required this.photo,
    required this.sending,
    required this.replay,
    required this.placeId,
    required this.pin,
    required this.onPin,
    required this.onRetake,
    required this.onSend,
  });

  final Uint8List photo;
  final bool sending;
  final bool replay;
  final String? placeId;
  final GeoPoint? pin;
  final ValueChanged<GeoPoint> onPin;
  final VoidCallback onRetake;
  final ValueChanged<GeoPoint> onSend;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    GeoPoint? location;
    Widget where;
    if (replay) {
      final places = ref.watch(placesProvider).value ?? const [];
      final chosen = places.where((p) => p.id == placeId).firstOrNull ?? places.firstOrNull;
      final start = chosen?.place.location ?? velachery;
      location = pin ?? start;
      where = Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Text(l.reportPinHint, style: const TextStyle(fontSize: 13, color: TideColors.muted)),
        const SizedBox(height: 8),
        ClipRRect(
          borderRadius: BorderRadius.circular(18),
          child: SizedBox(
            height: 200,
            child: Stack(children: [
              TideMap(
                segments: ref.watch(segmentsProvider).value ?? const <Segment>[],
                risk: const {},
                focus: start,
                zoom: 16,
                onCentre: onPin,
              ),
              IgnorePointer(
                child: Center(
                  child: Transform.translate(
                    offset: const Offset(0, -14),
                    child: nimbusIcon(NimbusIcon.drop, size: 28, color: TideColors.accent),
                  ),
                ),
              ),
            ]),
          ),
        ),
      ]);
    } else {
      final gps = ref.watch(currentPositionProvider);
      location = gps.value;
      where = gps.isLoading
          ? Text(AppLocalizations.of(context).findingYou, style: const TextStyle(color: TideColors.muted))
          : Text(location == null ? l.locationOff : l.usingYourLocation,
              style: TextStyle(color: location == null ? TideColors.watch : TideColors.muted));
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(22, 0, 22, 20),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(18),
          child: AspectRatio(aspectRatio: 4 / 3, child: Image.memory(photo, fit: BoxFit.cover, gaplessPlayback: true)),
        ),
        const SizedBox(height: 16),
        where,
        const SizedBox(height: 20),
        PillButton(
          label: sending ? l.sending : l.send,
          onTap: sending || location == null ? null : () => onSend(location!),
        ),
        PillButton(label: l.retake, quiet: true, onTap: sending ? null : onRetake),
      ]),
    );
  }
}

/// A failed send, explained: a Replay that hasn't started gets its own words.
class _FailedPanel extends StatelessWidget {
  const _FailedPanel({required this.e, required this.onRetry});

  final ApiException e;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final message = switch (e.code) {
      ApiException.runNotStarted => l.replayNotStarted,
      ApiException.photoNotUploaded => l.photoNotUploaded,
      _ => l.reportFailed,
    };
    return Padding(
      padding: const EdgeInsets.fromLTRB(28, 0, 28, 24),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        const Spacer(),
        Center(child: nimbusIcon(NimbusIcon.drop, size: 44, color: TideColors.muted)),
        const SizedBox(height: 16),
        Text(message, textAlign: TextAlign.center, style: const TextStyle(fontSize: 18, height: 1.35)),
        const Spacer(),
        PillButton(label: l.tryAgain, onTap: onRetry),
        PillButton(
          label: l.home,
          quiet: true,
          onTap: () => Navigator.of(context).popUntil((r) => r.isFirst),
        ),
      ]),
    );
  }
}
