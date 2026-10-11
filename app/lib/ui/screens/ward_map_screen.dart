import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../contracts/nimbus.dart';
import '../../l10n/app_localizations.dart';
import '../../state/providers.dart';
import '../icons.dart';
import '../theme/tide_colors.dart';
import '../widgets/band_chip.dart';
import '../widgets/round_button.dart';
import '../widgets/tide_map.dart';

/// The whole Ward: Segments by band, where water was seen, and Hazards with
/// their no-go rings. Risk polls on its own; Readings and Hazards refresh
/// every 10 s while the map is open.
class WardMapScreen extends ConsumerStatefulWidget {
  const WardMapScreen({super.key});

  @override
  ConsumerState<WardMapScreen> createState() => _WardMapScreenState();
}

class _WardMapScreenState extends ConsumerState<WardMapScreen> {
  Timer? _poll;

  @override
  void initState() {
    super.initState();
    _poll = Timer.periodic(const Duration(seconds: 10), (_) {
      ref.invalidate(readingsProvider);
      ref.invalidate(hazardsProvider);
    });
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final segments = ref.watch(segmentsProvider).value ?? const <Segment>[];
    final byId = {for (final s in segments) s.segmentId: s};
    final risk = ref.watch(riskProvider).value?.bySegment ?? const <String, SegmentRisk>{};
    final hazards = ref.watch(hazardsProvider).value ?? const <Hazard>[];
    final readings = ref.watch(readingsProvider).value ?? const <Reading>[];
    final marks = [
      for (final r in readings)
        if (byId[r.segmentId] case final s?) _middle(s.geometry),
    ];

    return Scaffold(
      body: Stack(children: [
        TideMap(segments: segments, risk: risk, hazards: hazards, waterMarks: marks, zoom: 15),
        SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Row(children: [
              RoundButton(
                size: 40,
                color: TideColors.deep,
                onTap: () => Navigator.of(context).maybePop(),
                child: nimbusIcon(NimbusIcon.back, size: 20),
              ),
              const SizedBox(width: 6),
              Text(l.wardMapTitle, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
            ]),
          ),
        ),
        Positioned(left: 12, right: 12, bottom: 0, child: SafeArea(top: false, child: _Legend(l: l))),
      ]),
    );
  }
}

GeoPoint _middle(LineString line) {
  final c = line.coordinates[line.coordinates.length ~/ 2];
  return GeoPoint(lat: c[1], lon: c[0]);
}

class _Legend extends StatelessWidget {
  const _Legend({required this.l});
  final AppLocalizations l;

  @override
  Widget build(BuildContext context) {
    Widget line(Color c, String label) => Row(mainAxisSize: MainAxisSize.min, children: [
          Container(width: 18, height: 4, decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(2))),
          const SizedBox(width: 6),
          Text(label, style: const TextStyle(fontSize: 11.5)),
        ]);
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: TideColors.deep.withValues(alpha: 0.88),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Wrap(spacing: 14, runSpacing: 8, children: [
        line(TideColors.low, bandName(RiskBand.LOW, l)),
        line(TideColors.watch, bandName(RiskBand.WATCH, l)),
        line(TideColors.likely, bandName(RiskBand.LIKELY, l)),
        line(TideColors.water, l.legendObserved),
        Row(mainAxisSize: MainAxisSize.min, children: [
          Container(
            width: 12,
            height: 12,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: const Color(0xFFFF4D4D), width: 1.5),
            ),
          ),
          const SizedBox(width: 6),
          Text(l.legendHazard, style: const TextStyle(fontSize: 11.5)),
        ]),
      ]),
    );
  }
}
