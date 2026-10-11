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
  const BandChip({super.key, required this.band, this.minutesToFlood, required this.l});

  final RiskBand band;
  final int? minutesToFlood;
  final AppLocalizations l;

  @override
  Widget build(BuildContext context) {
    final counts = band == RiskBand.LIKELY || band == RiskBand.WATCH;
    final minutes = minutesToFlood;
    final text = counts && minutes != null
        ? '${bandName(band, l)} · ${formatMinutes(minutes, l)}'
        : bandName(band, l);
    return Text(
      text,
      maxLines: 1,
      style: TextStyle(color: bandColor(band), fontWeight: FontWeight.w600, fontSize: 12.5),
    );
  }
}
