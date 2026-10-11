import 'package:flutter_test/flutter_test.dart';
import 'package:nimbus_app/contracts/nimbus.dart';
import 'package:nimbus_app/domain/place_view.dart';
import 'package:nimbus_app/domain/rank.dart';

import '../support/fixtures.dart';

void main() {
  final risk = fixtureRisk();
  List<String> labels(List<PlaceStatus> s) => [for (final p in s) p.view.place.label];

  test('rankPlaces puts flooded last and low first', () {
    final ranked = rankPlaces([
      place('pl-1', 'Bike parking', ['27480309-1']),
      place('pl-2', 'Office', ['27320162-0']),
      place('pl-3', 'Home', ['27480309-4']),
    ], risk);
    expect(labels(ranked), ['Office', 'Home', 'Bike parking']);
    expect([for (final p in ranked) p.severity], [0, 2, 3]);
    expect(ranked.last.worst!.band, RiskBand.FLOODED);
  });

  test('rankPlaces takes the worst Segment of a place', () {
    final ranked = rankPlaces([place('pl-1', 'Home', ['27320162-0', '27480309-4'])], risk);
    expect(ranked.single.worst!.segmentId, '27480309-4');
  });

  test('rankPlaces orders likely by minutesToFlood, null last', () {
    SegmentRisk likely(String id, int? minutes) => SegmentRisk(
          band: RiskBand.LIKELY,
          floodThresholdMm: 60,
          minutesToFlood: minutes,
          reasons: [],
          runId: 'replay-michaung',
          segmentId: id,
          score: 70,
          simTime: DateTime.utc(2023, 12, 3, 20, 30),
        );
    final ranked = rankPlaces([
      place('pl-a', 'Soon', ['s-20']),
      place('pl-b', 'Unknown', ['s-null']),
      place('pl-c', 'Later', ['s-90']),
    ], {
      's-20': likely('s-20', 20),
      's-null': likely('s-null', null),
      's-90': likely('s-90', 90),
    });
    // Display order: least urgent first, the most urgent at the bottom.
    expect(labels(ranked), ['Unknown', 'Later', 'Soon']);
  });

  test('rankPlaces breaks ties by label', () {
    final ranked = rankPlaces([
      place('pl-1', 'School', ['27320162-0']),
      place('pl-2', 'Gym', ['27320162-0']),
    ], risk);
    expect(labels(ranked), ['Gym', 'School']);
  });

  test('rankPlaces gives severity -1 to a place with no segments or no risk rows', () {
    final ranked = rankPlaces([
      place('pl-1', 'Far away', []),
      place('pl-2', 'Unscored', ['99999-0']),
      place('pl-3', 'Office', ['27320162-0']),
    ], risk);
    expect(labels(ranked), ['Far away', 'Unscored', 'Office']);
    expect(ranked[0].severity, -1);
    expect(ranked[0].worst, isNull);
    expect(ranked[1].severity, -1);
  });

  test('PlaceView reads run_ids and defaults to live', () {
    final json = place('pl-1', 'Home', ['27480309-1']).toJson();
    expect(json['run_ids'], ['replay-michaung']);
    expect(PlaceView.fromJson(json).runIds, ['replay-michaung']);
    expect(PlaceView.fromJson(json..remove('run_ids')).runIds, ['live']);
  });
}
