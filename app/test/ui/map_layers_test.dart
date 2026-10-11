import 'package:flutter_test/flutter_test.dart';
import 'package:nimbus_app/ui/widgets/map_layers.dart';

import '../support/fixtures.dart';

Map<String, dynamic> _feature(Map<String, dynamic> fc, String segmentId) =>
    (fc['features'] as List).cast<Map<String, dynamic>>().firstWhere((f) => f['properties']['segment_id'] == segmentId);

void main() {
  test('segmentsGeoJson colours 27480309-1 as water and 27480309-4 as likely', () {
    final fc = segmentsGeoJson(fixtureSegments(), fixtureRisk());
    expect(fc['type'], 'FeatureCollection');
    expect(fc['features'], hasLength(21));
    final flooded = _feature(fc, '27480309-1');
    expect(flooded['properties']['band'], 'flooded');
    expect(flooded['properties']['color'], '#59d8e6');
    expect(flooded['geometry']['type'], 'LineString');
    final likely = _feature(fc, '27480309-4');
    expect(likely['properties']['band'], 'likely');
    expect(likely['properties']['color'], '#ff7a57');
  });

  test('segmentsGeoJson marks Segments without risk and dims the ones not emphasised', () {
    final fc = segmentsGeoJson(fixtureSegments(), {}, emphasise: {'27480309-1'});
    expect(_feature(fc, '27480309-1')['properties'], containsPair('band', 'none'));
    expect(_feature(fc, '27480309-1')['properties'], containsPair('dim', false));
    expect(_feature(fc, '27480309-4')['properties'], containsPair('dim', true));
  });

  test('hazardsGeoJson carries no_go_radius_m 30', () {
    final fc = hazardsGeoJson(fixtureHazards());
    final f = (fc['features'] as List).single as Map<String, dynamic>;
    expect(f['geometry'], {'type': 'Point', 'coordinates': [80.2212061, 12.9777428]});
    expect(f['properties']['radius_m'], 30.0);
    expect(f['properties']['hazard_class'], 'open_manhole');
  });

  test('hazardRingsGeoJson draws a closed ring at the no-go radius', () {
    final fc = hazardRingsGeoJson(fixtureHazards());
    final coords = ((fc['features'] as List).single['geometry']['coordinates'] as List).cast<List<double>>();
    expect(coords.first, coords.last);
    // 30 m north of 12.9777428 is about 0.00027 degrees of latitude.
    final north = coords.map((c) => c[1]).reduce((a, b) => a > b ? a : b);
    expect(north - 12.9777428, closeTo(0.00027, 0.00001));
  });
}
