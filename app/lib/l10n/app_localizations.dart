import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';
import 'app_localizations_ta.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('ta'),
  ];

  /// No description provided for @appTagline.
  ///
  /// In en, this message translates to:
  /// **'Know before the water does'**
  String get appTagline;

  /// No description provided for @yourPlaces.
  ///
  /// In en, this message translates to:
  /// **'Your places'**
  String get yourPlaces;

  /// No description provided for @placesNeedYou.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 of your places needs you now} other{{count} of your places need you now}}'**
  String placesNeedYou(int count);

  /// No description provided for @allClear.
  ///
  /// In en, this message translates to:
  /// **'All your places are clear'**
  String get allClear;

  /// No description provided for @bandLow.
  ///
  /// In en, this message translates to:
  /// **'Low'**
  String get bandLow;

  /// No description provided for @bandWatch.
  ///
  /// In en, this message translates to:
  /// **'Watch'**
  String get bandWatch;

  /// No description provided for @bandLikely.
  ///
  /// In en, this message translates to:
  /// **'Likely'**
  String get bandLikely;

  /// No description provided for @bandFlooded.
  ///
  /// In en, this message translates to:
  /// **'Flooded'**
  String get bandFlooded;

  /// No description provided for @durationHm.
  ///
  /// In en, this message translates to:
  /// **'{h}h {m}m'**
  String durationHm(int h, int m);

  /// No description provided for @durationM.
  ///
  /// In en, this message translates to:
  /// **'{m}m'**
  String durationM(int m);

  /// No description provided for @report.
  ///
  /// In en, this message translates to:
  /// **'Report'**
  String get report;

  /// No description provided for @route.
  ///
  /// In en, this message translates to:
  /// **'Route'**
  String get route;

  /// No description provided for @map.
  ///
  /// In en, this message translates to:
  /// **'Map'**
  String get map;

  /// No description provided for @sos.
  ///
  /// In en, this message translates to:
  /// **'SOS'**
  String get sos;

  /// No description provided for @help.
  ///
  /// In en, this message translates to:
  /// **'Help'**
  String get help;

  /// No description provided for @verifying.
  ///
  /// In en, this message translates to:
  /// **'Verifying…'**
  String get verifying;

  /// No description provided for @dry.
  ///
  /// In en, this message translates to:
  /// **'Dry'**
  String get dry;

  /// No description provided for @ankleDeep.
  ///
  /// In en, this message translates to:
  /// **'Ankle-deep'**
  String get ankleDeep;

  /// No description provided for @kneeDeep.
  ///
  /// In en, this message translates to:
  /// **'Knee-deep'**
  String get kneeDeep;

  /// No description provided for @waistDeep.
  ///
  /// In en, this message translates to:
  /// **'Waist-deep'**
  String get waistDeep;

  /// No description provided for @aboveWaist.
  ///
  /// In en, this message translates to:
  /// **'Above the waist'**
  String get aboveWaist;

  /// No description provided for @taughtTheMap.
  ///
  /// In en, this message translates to:
  /// **'You taught the map.'**
  String get taughtTheMap;

  /// No description provided for @confirmedPrediction.
  ///
  /// In en, this message translates to:
  /// **'Your photo confirmed the prediction.'**
  String get confirmedPrediction;

  /// No description provided for @noSafeRoute.
  ///
  /// In en, this message translates to:
  /// **'No safe route'**
  String get noSafeRoute;

  /// No description provided for @replayNotStarted.
  ///
  /// In en, this message translates to:
  /// **'The Replay hasn\'t started yet. Start it, then try again.'**
  String get replayNotStarted;

  /// No description provided for @routingUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Routing is coming online. Try again in a minute.'**
  String get routingUnavailable;

  /// No description provided for @offlineUpdated.
  ///
  /// In en, this message translates to:
  /// **'Offline · updated {time}'**
  String offlineUpdated(String time);

  /// No description provided for @noStreetsNearby.
  ///
  /// In en, this message translates to:
  /// **'No streets nearby'**
  String get noStreetsNearby;

  /// No description provided for @noDataYet.
  ///
  /// In en, this message translates to:
  /// **'No data yet'**
  String get noDataYet;

  /// No description provided for @moveToHigherGround.
  ///
  /// In en, this message translates to:
  /// **'Move your vehicle to higher ground'**
  String get moveToHigherGround;

  /// No description provided for @skip.
  ///
  /// In en, this message translates to:
  /// **'Skip'**
  String get skip;

  /// No description provided for @continueLabel.
  ///
  /// In en, this message translates to:
  /// **'Continue'**
  String get continueLabel;

  /// No description provided for @chooseLanguage.
  ///
  /// In en, this message translates to:
  /// **'Choose your language'**
  String get chooseLanguage;

  /// No description provided for @allowAlertsTitle.
  ///
  /// In en, this message translates to:
  /// **'Get alerts for your streets'**
  String get allowAlertsTitle;

  /// No description provided for @allowAlertsBody.
  ///
  /// In en, this message translates to:
  /// **'We\'ll tell you before water reaches the places you care about.'**
  String get allowAlertsBody;

  /// No description provided for @allowAlerts.
  ///
  /// In en, this message translates to:
  /// **'Allow alerts'**
  String get allowAlerts;

  /// No description provided for @notNow.
  ///
  /// In en, this message translates to:
  /// **'Not now'**
  String get notNow;

  /// No description provided for @addFirstPlaceTitle.
  ///
  /// In en, this message translates to:
  /// **'Add a place you care about'**
  String get addFirstPlaceTitle;

  /// No description provided for @addFirstPlaceBody.
  ///
  /// In en, this message translates to:
  /// **'Home, office, school, or where your bike is parked.'**
  String get addFirstPlaceBody;

  /// No description provided for @addPlace.
  ///
  /// In en, this message translates to:
  /// **'Add a place'**
  String get addPlace;

  /// No description provided for @replayTag.
  ///
  /// In en, this message translates to:
  /// **'Replay'**
  String get replayTag;

  /// No description provided for @runLineReplay.
  ///
  /// In en, this message translates to:
  /// **'Replay · Cyclone Michaung · {time}'**
  String runLineReplay(String time);

  /// No description provided for @runLineReplayNoTime.
  ///
  /// In en, this message translates to:
  /// **'Replay · Cyclone Michaung'**
  String get runLineReplayNoTime;

  /// No description provided for @runLineLive.
  ///
  /// In en, this message translates to:
  /// **'Live · {time}'**
  String runLineLive(String time);

  /// No description provided for @runLineLiveNoTime.
  ///
  /// In en, this message translates to:
  /// **'Live'**
  String get runLineLiveNoTime;

  /// The language switch label: shows the other language.
  ///
  /// In en, this message translates to:
  /// **'த'**
  String get language;

  /// No description provided for @addAnotherPlace.
  ///
  /// In en, this message translates to:
  /// **'Add a place'**
  String get addAnotherPlace;

  /// No description provided for @showMeTheWay.
  ///
  /// In en, this message translates to:
  /// **'Show me the way'**
  String get showMeTheWay;

  /// No description provided for @edit.
  ///
  /// In en, this message translates to:
  /// **'Edit'**
  String get edit;

  /// No description provided for @whatToDo.
  ///
  /// In en, this message translates to:
  /// **'What to do'**
  String get whatToDo;

  /// No description provided for @whyLabel.
  ///
  /// In en, this message translates to:
  /// **'Why'**
  String get whyLabel;

  /// No description provided for @floodsIn.
  ///
  /// In en, this message translates to:
  /// **'Floods in about {time}'**
  String floodsIn(String time);

  /// No description provided for @wardMapTitle.
  ///
  /// In en, this message translates to:
  /// **'Velachery ward'**
  String get wardMapTitle;

  /// No description provided for @legendObserved.
  ///
  /// In en, this message translates to:
  /// **'Water seen'**
  String get legendObserved;

  /// No description provided for @legendHazard.
  ///
  /// In en, this message translates to:
  /// **'Hazard · keep out'**
  String get legendHazard;

  /// No description provided for @placeGone.
  ///
  /// In en, this message translates to:
  /// **'This place was removed.'**
  String get placeGone;

  /// No description provided for @back.
  ///
  /// In en, this message translates to:
  /// **'Back'**
  String get back;

  /// No description provided for @addPlaceTitle.
  ///
  /// In en, this message translates to:
  /// **'Add a place'**
  String get addPlaceTitle;

  /// No description provided for @editPlaceTitle.
  ///
  /// In en, this message translates to:
  /// **'Edit place'**
  String get editPlaceTitle;

  /// No description provided for @kindHome.
  ///
  /// In en, this message translates to:
  /// **'Home'**
  String get kindHome;

  /// No description provided for @kindOffice.
  ///
  /// In en, this message translates to:
  /// **'Office'**
  String get kindOffice;

  /// No description provided for @kindSchool.
  ///
  /// In en, this message translates to:
  /// **'School'**
  String get kindSchool;

  /// No description provided for @kindParking.
  ///
  /// In en, this message translates to:
  /// **'Parking'**
  String get kindParking;

  /// No description provided for @placeLabelHint.
  ///
  /// In en, this message translates to:
  /// **'Name this place'**
  String get placeLabelHint;

  /// No description provided for @pinHint.
  ///
  /// In en, this message translates to:
  /// **'Move the map to put the pin on the place'**
  String get pinHint;

  /// No description provided for @radiusLabel.
  ///
  /// In en, this message translates to:
  /// **'Watch streets within {metres} m'**
  String radiusLabel(int metres);

  /// No description provided for @save.
  ///
  /// In en, this message translates to:
  /// **'Save'**
  String get save;

  /// No description provided for @delete.
  ///
  /// In en, this message translates to:
  /// **'Delete'**
  String get delete;

  /// No description provided for @cancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get cancel;

  /// No description provided for @remove.
  ///
  /// In en, this message translates to:
  /// **'Remove'**
  String get remove;

  /// No description provided for @removePlaceTitle.
  ///
  /// In en, this message translates to:
  /// **'Remove this place?'**
  String get removePlaceTitle;

  /// No description provided for @removePlaceBody.
  ///
  /// In en, this message translates to:
  /// **'You\'ll stop getting alerts for it.'**
  String get removePlaceBody;

  /// No description provided for @tooManyPlaces.
  ///
  /// In en, this message translates to:
  /// **'You can save up to 20 places. Remove one to add another.'**
  String get tooManyPlaces;

  /// No description provided for @saveFailed.
  ///
  /// In en, this message translates to:
  /// **'Couldn\'t save. Check your connection and try again.'**
  String get saveFailed;

  /// No description provided for @findingYou.
  ///
  /// In en, this message translates to:
  /// **'Finding where you are…'**
  String get findingYou;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en', 'ta'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
    case 'ta':
      return AppLocalizationsTa();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
