import 'package:flutter/painting.dart';

import '../../contracts/nimbus.dart';

/// The Deep tide palette, exactly as fixed in app/docs/plan.md.
abstract final class TideColors {
  static const sky0 = Color(0xFF5F8FAE);
  static const sky1 = Color(0xFF3B6E93);
  static const sky2 = Color(0xFF1C4A75);
  static const deep = Color(0xFF0A1F44);

  /// Back to front.
  static const waves = <Color>[
    Color(0xFF3E78A0),
    Color(0xFF2E6690),
    Color(0xFF22557F),
    Color(0xFF18456E),
    Color(0xFF10365E),
    Color(0xFF0A2849),
  ];

  static const text = Color(0xFFFFFFFF);
  static const muted = Color(0xFFA9C6DB);
  static const accent = Color(0xFF4FD1D9);
  static const button = Color(0xFF2FA9B8);
  static const sos = Color(0xFFE8432A);

  // Predicted risk is warm; only observed water is cyan.
  static const low = Color(0xFFCFE3F0);
  static const watch = Color(0xFFF2B34A);
  static const likely = Color(0xFFFF7A57);
  static const water = Color(0xFF59D8E6);

  static const mapBg = Color(0xFF0C2347);
  static const mapRoad = Color(0xFF183764);
}

/// `FLOODED` comes only from a Reading, so it alone is drawn as water.
Color bandColor(RiskBand band) => switch (band) {
      RiskBand.LOW => TideColors.low,
      RiskBand.WATCH => TideColors.watch,
      RiskBand.LIKELY => TideColors.likely,
      RiskBand.FLOODED => TideColors.water,
    };
