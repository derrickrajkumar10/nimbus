import 'package:flutter/material.dart';

import '../../contracts/nimbus.dart';
import '../../l10n/app_localizations.dart';
import '../theme/tide_colors.dart';

String bandName(RiskBand band, AppLocalizations l) => switch (band) {
      RiskBand.LOW => l.bandLow,
      RiskBand.WATCH => l.bandWatch,
      RiskBand.LIKELY => l.bandLikely,
      RiskBand.FLOODED => l.bandFlooded,
    };

/// "1h 40m", or "40m" under an hour.
String formatMinutes(int minutes, AppLocalizations l) =>
    minutes >= 60 ? l.durationHm(minutes ~/ 60, minutes % 60) : l.durationM(minutes);

/// The band name in its colour, plus the countdown for `watch` and `likely`.
class BandChip extends StatelessWidget {
  const BandChip({super.key, required this.band, this.minutesToFlood, required this.l, this.stacked = false});

  final RiskBand band;
  final int? minutesToFlood;
  final AppLocalizations l;

  /// Band over countdown, right-aligned, as on Home's rows.
  final bool stacked;

  @override
  Widget build(BuildContext context) {
    final counts = band == RiskBand.LIKELY || band == RiskBand.WATCH;
    final minutes = minutesToFlood;
    final countdown = counts && minutes != null ? formatMinutes(minutes, l) : null;
    final style = TextStyle(color: bandColor(band), fontWeight: FontWeight.w600, fontSize: 12.5, height: 1.25);
    if (stacked) {
      return Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Text(bandName(band, l), maxLines: 1, style: style),
          if (countdown != null) Text(countdown, maxLines: 1, style: style),
        ],
      );
    }
    final text = countdown != null ? '${bandName(band, l)} · $countdown' : bandName(band, l);
    return Text(text, maxLines: 1, style: style);
  }
}
