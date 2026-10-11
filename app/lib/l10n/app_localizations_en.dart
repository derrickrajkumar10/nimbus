// ignore: unused_import
import 'package:intl/intl.dart' as intl;

import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appTagline => 'Know before the water does';

  @override
  String get yourPlaces => 'Your places';

  @override
  String placesNeedYou(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count of your places need you now',
      one: '1 of your places needs you now',
    );
    return '$_temp0';
  }

  @override
  String get allClear => 'All your places are clear';

  @override
  String get bandLow => 'Low';

  @override
  String get bandWatch => 'Watch';

  @override
  String get bandLikely => 'Likely';

  @override
  String get bandFlooded => 'Flooded';

  @override
  String durationHm(int h, int m) {
    return '${h}h ${m}m';
  }

  @override
  String durationM(int m) {
    return '${m}m';
  }

  @override
  String get report => 'Report';

  @override
  String get route => 'Route';

  @override
  String get map => 'Map';

  @override
  String get sos => 'SOS';

  @override
  String get help => 'Help';

  @override
  String get verifying => 'Verifying…';

  @override
  String get dry => 'Dry';

  @override
  String get ankleDeep => 'Ankle-deep';

  @override
  String get kneeDeep => 'Knee-deep';

  @override
  String get waistDeep => 'Waist-deep';

  @override
  String get aboveWaist => 'Above the waist';

  @override
  String get taughtTheMap => 'You taught the map.';

  @override
  String get confirmedPrediction => 'Your photo confirmed the prediction.';

  @override
  String get noSafeRoute => 'No safe route';

  @override
  String get replayNotStarted =>
      'The Replay hasn\'t started yet. Start it, then try again.';

  @override
  String get routingUnavailable =>
      'Routing is coming online. Try again in a minute.';

  @override
  String offlineUpdated(String time) {
    return 'Offline · updated $time';
  }

  @override
  String get noStreetsNearby => 'No streets nearby';

  @override
  String get noDataYet => 'No data yet';

  @override
  String get moveToHigherGround => 'Move your vehicle to higher ground';

  @override
  String get skip => 'Skip';

  @override
  String get continueLabel => 'Continue';

  @override
  String get chooseLanguage => 'Choose your language';

  @override
  String get allowAlertsTitle => 'Get alerts for your streets';

  @override
  String get allowAlertsBody =>
      'We\'ll tell you before water reaches the places you care about.';

  @override
  String get allowAlerts => 'Allow alerts';

  @override
  String get notNow => 'Not now';

  @override
  String get addFirstPlaceTitle => 'Add a place you care about';

  @override
  String get addFirstPlaceBody =>
      'Home, office, school, or where your bike is parked.';

  @override
  String get addPlace => 'Add a place';

  @override
  String get replayTag => 'Replay';

  @override
  String runLineReplay(String time) {
    return 'Replay · Cyclone Michaung · $time';
  }

  @override
  String get runLineReplayNoTime => 'Replay · Cyclone Michaung';

  @override
  String runLineLive(String time) {
    return 'Live · $time';
  }

  @override
  String get runLineLiveNoTime => 'Live';

  @override
  String get language => 'த';

  @override
  String get addAnotherPlace => 'Add a place';

  @override
  String get showMeTheWay => 'Show me the way';

  @override
  String get edit => 'Edit';

  @override
  String get whatToDo => 'What to do';

  @override
  String get whyLabel => 'Why';

  @override
  String floodsIn(String time) {
    return 'Floods in about $time';
  }

  @override
  String get wardMapTitle => 'Velachery ward';

  @override
  String get legendObserved => 'Water seen';

  @override
  String get legendHazard => 'Hazard · keep out';

  @override
  String get placeGone => 'This place was removed.';

  @override
  String get back => 'Back';
}
