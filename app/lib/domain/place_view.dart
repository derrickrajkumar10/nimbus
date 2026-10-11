import '../contracts/nimbus.dart';

/// A Saved Place as the citizen API returns it: the contract `SavedPlace`
/// plus the `run_ids` the API adds (which Runs alert this place).
class PlaceView {
  const PlaceView({required this.place, required this.runIds});

  final SavedPlace place;
  final List<String> runIds;

  String get id => place.placeId;

  factory PlaceView.fromJson(Map<String, dynamic> j) => PlaceView(
        place: SavedPlace.fromJson(j),
        runIds: List<String>.from(j['run_ids'] ?? const ['live']),
      );

  Map<String, dynamic> toJson() => {...place.toJson(), 'run_ids': runIds};
}
