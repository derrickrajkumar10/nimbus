import 'package:intl/intl.dart';

const _ist = Duration(hours: 5, minutes: 30);

/// Storm times are shown in IST, whatever the phone's zone.
DateTime _inIst(DateTime t) => t.toUtc().add(_ist);

/// "4 Dec 02:00".
String stormTime(DateTime t, String locale) => DateFormat('d MMM HH:mm', locale).format(_inIst(t));

/// "02:00".
String clockTime(DateTime t) => DateFormat('HH:mm').format(_inIst(t));
