import 'package:flutter/widgets.dart';
import 'package:flutter_svg/flutter_svg.dart';

import 'theme/tide_colors.dart';

/// The app's own line icon set: 24 px grid, 1.8 px stroke, round caps and
/// joins. Paths come from the `I` dict in app/docs/mockups/gen_styles.py.
enum NimbusIcon {
  bell('M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9M10.3 21a1.94 1.94 0 0 0 3.4 0'),
  camera('M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3z'
      'M15 13a3 3 0 1 1-6 0 3 3 0 0 1 6 0'),
  route('M6 21a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM18 7a2 2 0 1 0 0-4 2 2 0 0 0 0 4z'
      'M6 17V11a4 4 0 0 1 4-4h6M18 7v6a4 4 0 0 1-4 4h-6'),
  map('M9 4 3 6v14l6-2 6 2 6-2V4l-6 2zM9 4v14M15 6v14'),
  home('M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z'),
  arrow('M7 17 17 7M8 7h9v9'),
  back('M15 18l-6-6 6-6'),
  check('M5 12.5l4.5 4.5L19 7.5'),
  x('M6 6l12 12M18 6 6 18'),
  drop('M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z'),
  bike('M5.5 20a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM18.5 20a3 3 0 1 0 0-6 3 3 0 0 0 0 6z'
      'M5.5 17l3.5-7h5l4.5 7M9 10 7.5 7H6M14 10l-1.5-3H15'),
  car('M4 16v-4l2-5h12l2 5v4zM3 16h18M6.5 16v2.5M17.5 16v2.5M7.5 12.5h.01M16.5 12.5h.01'),
  ambulance('M2 17V7h12v10M14 10h4l4 4v3h-8M5 12h6M8 9v6M6 19.5a1.5 1.5 0 1 0 0-3'
      'M17 19.5a1.5 1.5 0 1 0 0-3'),
  warn('M12 4 2.5 20h19zM12 10v4.5M12 17.5h.01'),
  school('M3 9l9-5 9 5-9 5zM7 11v5c0 1 2.5 3 5 3s5-2 5-3v-5'),
  office('M4 21V5a1 1 0 0 1 1-1h9a1 1 0 0 1 1 1v16M15 9h4a1 1 0 0 1 1 1v11M8 8h3M8 12h3M8 16h3M3 21h18'),
  rain('M8 19l-1 2M12 19l-1 2M16 19l-1 2M7 16a5 5 0 1 1 1-9.9A6 6 0 0 1 19 9a3.5 3.5 0 0 1-1 7z'),
  parking('M3 5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z'
      'M9.5 17V7h3.5a3 3 0 0 1 0 6H9.5');

  const NimbusIcon(this.path);
  final String path;

  String get svg => '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
      'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
      '<path d="$path"/></svg>';
}

Widget nimbusIcon(NimbusIcon icon, {double size = 18, Color? color}) => SvgPicture.string(
      icon.svg,
      width: size,
      height: size,
      theme: SvgTheme(currentColor: color ?? TideColors.text),
    );
