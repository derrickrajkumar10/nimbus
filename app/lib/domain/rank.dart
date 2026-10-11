import '../contracts/nimbus.dart';
import 'place_view.dart';

/// A place with the worst risk among its Segments.
class PlaceStatus {
  const PlaceStatus({required this.view, required this.worst, required this.severity});

  final PlaceView view;

  /// Null when no Segment of the place has a risk row.
  final SegmentRisk? worst;

  /// FLOODED 3, LIKELY 2, WATCH 1, LOW 0, and -1 with no risk row.
  final int severity;
}

int severityOf(RiskBand band) => switch (band) {
      RiskBand.FLOODED => 3,
      RiskBand.LIKELY => 2,
      RiskBand.WATCH => 1,
      RiskBand.LOW => 0,
    };

/// Positive when [a] is more urgent than [b]: higher band, then a shorter
/// known time to flood (unknown counts as least urgent).
int _urgency(SegmentRisk a, SegmentRisk b) {
  final bySeverity = severityOf(a.band).compareTo(severityOf(b.band));
  if (bySeverity != 0) return bySeverity;
  final ma = a.minutesToFlood, mb = b.minutesToFlood;
  if (ma == mb) return 0;
  if (ma == null) return -1;
  if (mb == null) return 1;
  return mb.compareTo(ma);
}

/// Places in display order: least severe first, the worst last (Home puts
/// the worst on the deepest wave, at the bottom).
List<PlaceStatus> rankPlaces(List<PlaceView> places, Map<String, SegmentRisk> riskBySegment) {
  final statuses = [
    for (final view in places) _status(view, riskBySegment),
  ];
  statuses.sort((a, b) {
    final wa = a.worst, wb = b.worst;
    if (wa == null || wb == null) {
      final byRow = (wa == null ? 0 : 1).compareTo(wb == null ? 0 : 1);
      if (byRow != 0) return byRow;
    } else {
      final byUrgency = _urgency(wa, wb);
      if (byUrgency != 0) return byUrgency;
    }
    return a.view.place.label.compareTo(b.view.place.label);
  });
  return statuses;
}

PlaceStatus _status(PlaceView view, Map<String, SegmentRisk> riskBySegment) {
  SegmentRisk? worst;
  for (final id in view.place.segmentIds) {
    final r = riskBySegment[id];
    if (r != null && (worst == null || _urgency(r, worst) > 0)) worst = r;
  }
  return PlaceStatus(view: view, worst: worst, severity: worst == null ? -1 : severityOf(worst.band));
}
