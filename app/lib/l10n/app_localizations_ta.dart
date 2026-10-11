// ignore: unused_import
import 'package:intl/intl.dart' as intl;

import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Tamil (`ta`).
class AppLocalizationsTa extends AppLocalizations {
  AppLocalizationsTa([String locale = 'ta']) : super(locale);

  @override
  String get appTagline => 'நீர் வரும் முன் அறிந்திடுங்கள்';

  @override
  String get yourPlaces => 'உங்கள் இடங்கள்';

  @override
  String placesNeedYou(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'உங்கள் இடங்களில் $count இடங்களுக்கு இப்போது கவனம் தேவை',
      one: 'உங்கள் இடங்களில் ஒன்றுக்கு இப்போது கவனம் தேவை',
    );
    return '$_temp0';
  }

  @override
  String get allClear => 'உங்கள் இடங்கள் அனைத்தும் பாதுகாப்பாக உள்ளன';

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

  @override
  String get report => 'பதிவு';

  @override
  String get route => 'வழி';

  @override
  String get map => 'வரைபடம்';

  @override
  String get sos => 'SOS';

  @override
  String get help => 'உதவி';

  @override
  String get verifying => 'சரிபார்க்கிறது…';

  @override
  String get dry => 'நீர் இல்லை';

  @override
  String get ankleDeep => 'கணுக்கால் அளவு நீர்';

  @override
  String get kneeDeep => 'முழங்கால் அளவு நீர்';

  @override
  String get waistDeep => 'இடுப்பு அளவு நீர்';

  @override
  String get aboveWaist => 'இடுப்புக்கு மேல் நீர்';

  @override
  String get taughtTheMap => 'நீங்கள் வரைபடத்துக்குக் கற்றுக்கொடுத்தீர்கள்.';

  @override
  String get confirmedPrediction => 'உங்கள் படம் கணிப்பை உறுதிப்படுத்தியது.';

  @override
  String get noSafeRoute => 'பாதுகாப்பான வழி இல்லை';

  @override
  String get replayNotStarted =>
      'மறுஇயக்கம் இன்னும் தொடங்கவில்லை. அதைத் தொடங்கிவிட்டு மீண்டும் முயலுங்கள்.';

  @override
  String get routingUnavailable =>
      'வழிகாட்டல் விரைவில் இயங்கும். ஒரு நிமிடத்தில் மீண்டும் முயலுங்கள்.';

  @override
  String offlineUpdated(String time) {
    return 'இணைப்பு இல்லை · $time நிலவரம்';
  }

  @override
  String get noStreetsNearby => 'அருகில் தெருக்கள் இல்லை';

  @override
  String get noDataYet => 'இன்னும் தரவு இல்லை';

  @override
  String get moveToHigherGround =>
      'உங்கள் வாகனத்தை மேடான இடத்துக்கு நகர்த்துங்கள்';

  @override
  String get skip => 'தவிர்';

  @override
  String get continueLabel => 'தொடர்க';

  @override
  String get chooseLanguage => 'மொழியைத் தேர்ந்தெடுங்கள்';

  @override
  String get allowAlertsTitle =>
      'உங்கள் தெருக்களுக்கான எச்சரிக்கைகளைப் பெறுங்கள்';

  @override
  String get allowAlertsBody =>
      'நீங்கள் அக்கறை கொள்ளும் இடங்களை நீர் அடையும் முன் சொல்வோம்.';

  @override
  String get allowAlerts => 'எச்சரிக்கைகளை அனுமதி';

  @override
  String get notNow => 'இப்போது வேண்டாம்';

  @override
  String get addFirstPlaceTitle =>
      'உங்களுக்கு முக்கியமான ஓர் இடத்தைச் சேருங்கள்';

  @override
  String get addFirstPlaceBody =>
      'வீடு, அலுவலகம், பள்ளி, அல்லது உங்கள் பைக் நிறுத்தும் இடம்.';

  @override
  String get addPlace => 'இடத்தைச் சேர்';

  @override
  String get replayTag => 'மறுஇயக்கம்';

  @override
  String runLineReplay(String time) {
    return 'மறுஇயக்கம் · மிக்ஜாம் புயல் · $time';
  }

  @override
  String get runLineReplayNoTime => 'மறுஇயக்கம் · மிக்ஜாம் புயல்';

  @override
  String runLineLive(String time) {
    return 'நேரலை · $time';
  }

  @override
  String get runLineLiveNoTime => 'நேரலை';

  @override
  String get language => 'En';

  @override
  String get addAnotherPlace => 'இடத்தைச் சேர்';
}
