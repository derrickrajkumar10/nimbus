import '../contracts/nimbus.dart';

// Server reasons are English with the numbers baked in, so Tamil mode shows a
// line per code without the numbers. Derrick reviews the Tamil.
const _tamilByCode = {
  'antecedent_rain': 'கடந்த 72 மணி நேர மழையால் நிலம் நனைந்துள்ளது',
  'forecast_exceeds_threshold': 'வரவிருக்கும் மழை இந்தத் தெருவின் வெள்ள அளவைத் தாண்டும்',
  'forecast_below_threshold': 'வரவிருக்கும் மழை வெள்ள அளவுக்குக் கீழே உள்ளது',
  'heavy_rain': 'கனமழை பெய்கிறது',
  'rain_exceeds_threshold': 'பெய்த மழை இந்தத் தெருவின் வெள்ள அளவைத் தாண்டிவிட்டது',
  'nearby_reading': 'அருகில் நீர் அளவு பதிவாகியுள்ளது',
};

/// The reason in the user's language, falling back to the server's English.
String reasonLine(Reason r, String languageCode) =>
    languageCode == 'ta' ? (_tamilByCode[r.code] ?? r.text) : r.text;
