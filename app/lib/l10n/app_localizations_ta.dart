// ignore: unused_import
import 'package:intl/intl.dart' as intl;

import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Tamil (`ta`).
class AppLocalizationsTa extends AppLocalizations {
  AppLocalizationsTa([String locale = 'ta']) : super(locale);

  @override
  String get bandLow => 'குறைவு';

  @override
  String get bandWatch => 'கவனம்';

  @override
  String get bandLikely => 'வாய்ப்பு அதிகம்';

  @override
  String get bandFlooded => 'வெள்ளம்';

  @override
  String durationHm(int h, int m) {
    return '$h மணி $m நிமி';
  }

  @override
  String durationM(int m) {
    return '$m நிமி';
  }
}
