import 'dart:convert';
import 'dart:io';

import 'package:nimbus_app/contracts/nimbus.dart';
import 'package:nimbus_app/domain/place_view.dart';

/// Fixtures read straight from the synced assets, for pure-Dart tests.
List<Map<String, dynamic>> fixtureJson(String name) =>
    (jsonDecode(File('assets/fixtures/$name').readAsStringSync()) as List).cast<Map<String, dynamic>>();

List<Segment> fixtureSegments() => fixtureJson('segments.json').map(Segment.fromJson).toList();

Map<String, SegmentRisk> fixtureRisk() => {
      for (final r in fixtureJson('risk.json').map(SegmentRisk.fromJson)) r.segmentId: r,
    };

Reading fixtureReading() => Reading.fromJson(fixtureJson('readings.json').first);

List<Hazard> fixtureHazards() => fixtureJson('hazards.json').map(Hazard.fromJson).toList();

PlaceView place(
  String id,
  String label,
  List<String> segmentIds, {
  SavedPlaceKind kind = SavedPlaceKind.HOME,
  List<String> runIds = const ['replay-michaung'],
}) =>
    PlaceView(
      place: SavedPlace(
        deviceId: 'inst-test',
        kind: kind,
        label: label,
        location: GeoPoint(lat: 12.975, lon: 80.219),
        placeId: id,
        radiusM: 150,
        segmentIds: segmentIds,
      ),
      runIds: runIds,
    );
