import 'package:flutter_test/flutter_test.dart';
import 'package:nimbus_app/contracts/nimbus.dart';
import 'package:nimbus_app/domain/alert_routing.dart';
import 'package:nimbus_app/domain/depth.dart';
import 'package:nimbus_app/domain/geo.dart';
import 'package:nimbus_app/domain/reasons.dart';
import 'package:nimbus_app/domain/threshold_story.dart';

import '../support/fixtures.dart';

void main() {
  final places = [
    place('pl-home', 'Home', ['27320162-0']),
    place('pl-bike', 'Bike parking', ['27480309-1', '27480309-2']),
  ];

  test('placeIdForAlert matches by segment_id', () {
    expect(placeIdForAlert({'alert_id': 'al-1', 'segment_id': '27480309-2'}, places), 'pl-bike');
  });

  test('placeIdForAlert returns null for an unknown or missing segment_id', () {
    expect(placeIdForAlert({'alert_id': 'al-1', 'segment_id': '11111-0'}, places), isNull);
    expect(placeIdForAlert({'alert_id': 'al-1'}, places), isNull);
    expect(placeIdForAlert({'alert_id': 'al-1', 'segment_id': '27480309-1'}, []), isNull);
  });

  test('reasonLine returns Tamil by code and English for an unknown code', () {
    final known = Reason(code: 'heavy_rain', text: 'Heavy rain: 42 mm in the last hour');
    final unknown = Reason(code: 'tide_backflow', text: 'Sea tide is backing up the drains');
    expect(reasonLine(known, 'en'), 'Heavy rain: 42 mm in the last hour');
    expect(reasonLine(known, 'ta'), 'கனமழை பெய்கிறது');
    expect(reasonLine(unknown, 'ta'), 'Sea tide is backing up the drains');
    for (final code in [
      'antecedent_rain',
      'forecast_below_threshold',
      'forecast_exceeds_threshold',
      'heavy_rain',
      'rain_exceeds_threshold',
      'nearby_reading',
    ]) {
      expect(reasonLine(Reason(code: code, text: 'x'), 'ta'), isNot('x'), reason: code);
    }
  });

  test('thresholdStory on fixture 27480309-1 is not learned (67.5 → 67.5)', () {
    final segment = fixtureSegments().firstWhere((s) => s.segmentId == '27480309-1');
    final story = thresholdStory(segment, fixtureRisk()['27480309-1']!);
    expect(story.from, 67.5);
    expect(story.to, 67.5);
    expect(story.learned, isFalse);
  });

  test('thresholdStory 68 → 55 is learned', () {
    expect(const ThresholdStory(from: 68, to: 55).learned, isTrue);
    expect(const ThresholdStory(from: 68, to: 67.8).learned, isFalse);
  });

  test('waterFraction knee is 0.28', () {
    expect(waterFraction(DepthBand.KNEE), 0.28);
    expect(waterFraction(DepthBand.DRY), 0);
    expect(waterFraction(DepthBand.ABOVE_WAIST), 0.72);
  });

  test('segmentsNear finds 27480309-1 within 150 m of the hazard point 12.9777428, 80.2212061', () {
    final ids = segmentsNear(GeoPoint(lat: 12.9777428, lon: 80.2212061), 150, fixtureSegments());
    expect(ids, contains('27480309-1'));
  });

  test('segmentsNear falls back to the nearest Segment within 500 m, else none', () {
    final segments = fixtureSegments();
    // About 33 m off the street, a 1 m radius catches nothing, so the
    // nearest Segment is used.
    final tight = segmentsNear(GeoPoint(lat: 12.9780428, lon: 80.2212061), 1, segments);
    expect(tight, hasLength(1));
    expect(segmentsNear(GeoPoint(lat: 13.0827, lon: 80.2707), 150, segments), isEmpty);
  });

  test('distanceM is about 111 km per degree of latitude', () {
    expect(distanceM(GeoPoint(lat: 12, lon: 80), GeoPoint(lat: 13, lon: 80)), closeTo(111195, 200));
  });
}
