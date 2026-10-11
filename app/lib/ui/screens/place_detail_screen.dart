import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../contracts/nimbus.dart';
import '../../domain/rank.dart';
import '../../domain/reasons.dart';
import '../../l10n/app_localizations.dart';
import '../../state/providers.dart';
import '../icons.dart';
import '../routes.dart';
import '../theme/tide_colors.dart';
import '../widgets/band_chip.dart';
import '../widgets/pill_button.dart';
import '../widgets/round_button.dart';
import '../widgets/tide_background.dart';
import '../widgets/tide_map.dart';

/// The action for a place: the last alert's body (the Herald works out the
/// safer street), else a band-based line for `likely` and `flooded`.
String? actionLine(PlaceStatus s, String? lastAlert, AppLocalizations l) {
  if (lastAlert != null) return lastAlert;
  final band = s.worst?.band;
  return band == RiskBand.LIKELY || band == RiskBand.FLOODED ? l.moveToHigherGround : null;
}

/// One Saved Place: its streets on the map, why it's at risk, and what to do.
class PlaceDetailScreen extends ConsumerWidget {
  const PlaceDetailScreen({super.key, required this.placeId});

  final String placeId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final places = ref.watch(placesProvider).value ?? const [];
    final view = places.where((p) => p.id == placeId).firstOrNull;
    final snapshot = ref.watch(riskProvider).value ?? RiskSnapshot.empty;
    final segments = ref.watch(segmentsProvider).value ?? const <Segment>[];
    final hazards = ref.watch(hazardsProvider).value ?? const <Hazard>[];

    if (view == null) {
      return Scaffold(
        body: TideBackground(
          layerTops: const [0.6, 0.7, 0.8, 0.9],
          child: SafeArea(child: Center(child: Text(l.placeGone, style: const TextStyle(color: TideColors.muted)))),
        ),
      );
    }

    final status = rankPlaces([view], snapshot.bySegment).single;
    final worst = status.worst;
    final action = actionLine(status, ref.watch(lastAlertProvider)[placeId], l);
    final reasons = worst?.reasons.take(3).toList() ?? const <Reason>[];

    return Scaffold(
      body: LayoutBuilder(builder: (context, box) {
        final mapHeight = box.maxHeight * 0.46;
        // The body's constraints are loose: without expand the Stack would
        // end under the map and clip the panel to 40 px.
        return Stack(fit: StackFit.expand, children: [
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            height: mapHeight + 40,
            child: TideMap(
              segments: segments,
              risk: snapshot.bySegment,
              hazards: hazards,
              focus: view.place.location,
              zoom: 16,
              emphasise: view.place.segmentIds.toSet(),
              points: {'': view.place.location},
            ),
          ),
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: SafeArea(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Row(children: [
                  RoundButton(
                    size: 40,
                    color: TideColors.deep,
                    onTap: () => Navigator.of(context).maybePop(),
                    child: nimbusIcon(NimbusIcon.back, size: 20),
                  ),
                  const Spacer(),
                  RoundButton(
                    size: 40,
                    color: TideColors.deep,
                    onTap: () => Navigator.of(context).pushNamed(Routes.placeEdit, arguments: placeId),
                    child: Text(l.edit, style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w600)),
                  ),
                ]),
              ),
            ),
          ),
          Positioned.fill(
            top: mapHeight,
            child: TideBackground(
              layerTops: const [0.0, 0.05, 0.10],
              colors: const [Color(0xFF22557F), Color(0xFF18456E), Color(0xFF10365E)],
              rain: false,
              child: SafeArea(
                top: false,
                child: SingleChildScrollView(
                  padding: const EdgeInsets.fromLTRB(22, 46, 22, 20),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(view.place.label,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w600, height: 1.1)),
                    const SizedBox(height: 6),
                    if (worst == null)
                      Text(view.place.segmentIds.isEmpty ? l.noStreetsNearby : l.noDataYet,
                          style: const TextStyle(color: TideColors.muted))
                    else ...[
                      BandChip(band: worst.band, l: l),
                      if (worst.band != RiskBand.FLOODED && worst.minutesToFlood != null)
                        Padding(
                          padding: const EdgeInsets.only(top: 2),
                          child: Text(l.floodsIn(formatMinutes(worst.minutesToFlood!, l)),
                              style: TextStyle(fontSize: 15, color: bandColor(worst.band))),
                        ),
                    ],
                    if (reasons.isNotEmpty) ...[
                      const SizedBox(height: 18),
                      _Label(l.whyLabel),
                      for (final r in reasons)
                        Padding(
                          padding: const EdgeInsets.only(top: 6),
                          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            Padding(
                              padding: const EdgeInsets.only(top: 2),
                              child: nimbusIcon(NimbusIcon.rain, size: 14, color: TideColors.muted),
                            ),
                            const SizedBox(width: 8),
                            Expanded(child: Text(reasonLine(r, l.localeName), style: const TextStyle(fontSize: 14))),
                          ]),
                        ),
                    ],
                    if (action != null) ...[
                      const SizedBox(height: 18),
                      _Label(l.whatToDo),
                      const SizedBox(height: 6),
                      Text(action, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w500, height: 1.25)),
                    ],
                    const SizedBox(height: 22),
                    PillButton(
                      label: l.showMeTheWay,
                      onTap: () => Navigator.of(context).pushNamed(Routes.route, arguments: placeId),
                    ),
                  ]),
                ),
              ),
            ),
          ),
        ]);
      }),
    );
  }
}

class _Label extends StatelessWidget {
  const _Label(this.text);
  final String text;

  @override
  Widget build(BuildContext context) => Text(text.toUpperCase(),
      style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 0.9, color: TideColors.muted));
}
