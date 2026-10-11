import 'place_view.dart';

/// The Saved Place a push is about: the first whose Segments contain the
/// push's `segment_id`. Null sends the user to Home.
String? placeIdForAlert(Map<String, dynamic> data, List<PlaceView> places) {
  final segmentId = data['segment_id'];
  if (segmentId is! String) return null;
  for (final p in places) {
    if (p.place.segmentIds.contains(segmentId)) return p.id;
  }
  return null;
}
