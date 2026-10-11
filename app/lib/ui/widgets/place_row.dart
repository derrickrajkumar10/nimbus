import 'package:flutter/material.dart';

import '../../contracts/nimbus.dart';
import '../../domain/rank.dart';
import '../../domain/reasons.dart';
import '../../l10n/app_localizations.dart';
import '../icons.dart';
import '../theme/tide_colors.dart';
import 'band_chip.dart';

NimbusIcon kindIcon(SavedPlaceKind kind) => switch (kind) {
      SavedPlaceKind.HOME => NimbusIcon.home,
      SavedPlaceKind.OFFICE => NimbusIcon.office,
      SavedPlaceKind.SCHOOL => NimbusIcon.school,
      SavedPlaceKind.VEHICLE_PARKING => NimbusIcon.parking,
      SavedPlaceKind.OTHER => NimbusIcon.drop,
    };

/// The line under a place's name: the last alert's body (the Herald's
/// action), else its top reason, else why there's nothing to say.
String placeSubline(PlaceStatus s, String? lastAlert, AppLocalizations l) {
  if (lastAlert != null) return lastAlert;
  final worst = s.worst;
  if (worst != null && worst.reasons.isNotEmpty) return reasonLine(worst.reasons.first, l.localeName);
  return s.view.place.segmentIds.isEmpty ? l.noStreetsNearby : l.noDataYet;
}

/// One Saved Place sitting on its wave.
class PlaceRow extends StatelessWidget {
  const PlaceRow({super.key, required this.status, required this.lastAlert, required this.onTap});

  final PlaceStatus status;
  final String? lastAlert;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final worst = status.worst;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(14),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          children: [
            Container(
              width: 34,
              height: 34,
              alignment: Alignment.center,
              decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.12), shape: BoxShape.circle),
              child: nimbusIcon(kindIcon(status.view.place.kind), size: 17),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(status.view.place.label,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
                  Text(placeSubline(status, lastAlert, l),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 11, color: TideColors.muted)),
                ],
              ),
            ),
            if (worst != null) ...[
              const SizedBox(width: 10),
              BandChip(band: worst.band, minutesToFlood: worst.minutesToFlood, l: l, stacked: true),
            ],
          ],
        ),
      ),
    );
  }
}
