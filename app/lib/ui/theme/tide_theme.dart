import 'package:flutter/material.dart';

import 'tide_colors.dart';

const outfit = 'Outfit';
const notoTamil = 'NotoSansTamil';

/// Deep tide on Material 3. Both fonts are bundled; each falls back to the
/// other, so Tamil lines in English mode (and Latin numbers in Tamil) render.
ThemeData tideTheme(Locale locale) {
  final tamil = locale.languageCode == 'ta';
  final family = tamil ? notoTamil : outfit;
  final fallback = [tamil ? outfit : notoTamil];
  final base = ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    fontFamily: family,
    fontFamilyFallback: fallback,
    scaffoldBackgroundColor: TideColors.deep,
    colorScheme: const ColorScheme.dark(
      primary: TideColors.button,
      onPrimary: TideColors.text,
      secondary: TideColors.accent,
      error: TideColors.sos,
      surface: TideColors.deep,
      onSurface: TideColors.text,
      onSurfaceVariant: TideColors.muted,
    ),
  );
  return base.copyWith(
    textTheme: base.textTheme.apply(
      bodyColor: TideColors.text,
      displayColor: TideColors.text,
      fontFamily: family,
      fontFamilyFallback: fallback,
    ),
    sliderTheme: const SliderThemeData(
      activeTrackColor: TideColors.accent,
      thumbColor: TideColors.accent,
      inactiveTrackColor: Color(0x33FFFFFF),
    ),
    snackBarTheme: SnackBarThemeData(
      backgroundColor: TideColors.waves.last,
      contentTextStyle: const TextStyle(color: TideColors.text),
      behavior: SnackBarBehavior.floating,
    ),
  );
}
