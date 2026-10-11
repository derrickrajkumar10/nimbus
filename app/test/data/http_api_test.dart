import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:nimbus_app/contracts/nimbus.dart';
import 'package:nimbus_app/data/api_exception.dart';
import 'package:nimbus_app/data/fixture_api.dart';
import 'package:nimbus_app/data/http_api.dart';

import '../support/file_bundle.dart';
import '../support/fixtures.dart';

final _base = Uri.parse('https://citizen.example.com/');
const _install = 'inst-0123456789abcdef0123456789abcdef';

HttpNimbusApi _api(MockClientHandler handler) => HttpNimbusApi(
      _base,
      _install,
      client: MockClient(handler),
      fixtures: FixtureNimbusApi(FileBundle(), delay: Duration.zero),
    );

http.Response _json(Object body, [int status = 200]) => http.Response(
      jsonEncode(body),
      status,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );

void main() {
  test('sends X-Install-Id and run_id', () async {
    final seen = <http.Request>[];
    final api = _api((req) async {
      seen.add(req);
      return _json(req.url.path == '/risk' ? fixtureJson('risk.json') : <Object>[]);
    });

    final risk = await api.risk('replay-michaung');
    await api.savedPlaces();

    expect(risk, hasLength(21));
    expect(seen[0].url.path, '/risk');
    expect(seen[0].url.queryParameters['run_id'], 'replay-michaung');
    expect(seen[1].url.path, '/saved-places');
    expect(seen[1].headers['X-Install-Id'], _install);
  });

  test('maps a 409 run_not_started body to ApiException(code: run_not_started)', () async {
    final api = _api((_) async =>
        _json({'error': 'run_not_started', 'message': 'replay-michaung has no storm time yet'}, 409));
    final call = api.createSos(
      sosId: 'sos-01HZX3ABCDEFGHJKMNPQRSTVWX',
      runId: 'replay-michaung',
      location: GeoPoint(lat: 12.975, lon: 80.219),
      peopleCount: 3,
      flags: VulnerabilityFlags(elderly: true),
    );
    await expectLater(
      call,
      throwsA(isA<ApiException>()
          .having((e) => e.status, 'status', 409)
          .having((e) => e.code, 'code', 'run_not_started')),
    );
  });

  test('maps SocketException to ApiException(code: offline)', () async {
    final api = _api((_) async => throw const SocketException('Network is unreachable'));
    await expectLater(
      api.risk('live'),
      throwsA(isA<ApiException>().having((e) => e.status, 'status', 0).having((e) => e.code, 'code', 'offline')),
    );
  });

  test('hazards falls back to fixtures on 404', () async {
    final api = _api((_) async => _json({'error': 'not_found', 'message': 'no route for /hazards'}, 404));
    final hazards = await api.hazards('replay-michaung');
    expect(hazards.single.hazardId, 'hz-0001');
  });

  test('putPlace sends run_ids and parses PlaceView', () async {
    late http.Request sent;
    final api = _api((req) async {
      sent = req;
      final body = jsonDecode(req.body) as Map<String, dynamic>;
      return _json({
        'place_id': 'pl-1',
        'device_id': _install,
        'segment_ids': ['27480309-1'],
        ...body,
      });
    });

    final view = await api.putPlace(
      'pl-1',
      label: 'Bike parking',
      kind: SavedPlaceKind.VEHICLE_PARKING,
      location: GeoPoint(lat: 12.9777, lon: 80.2212),
      radiusM: 150,
      runIds: ['replay-michaung'],
    );

    expect(sent.method, 'PUT');
    expect(sent.url.path, '/saved-places/pl-1');
    expect(sent.headers['X-Install-Id'], _install);
    expect(jsonDecode(sent.body), {
      'label': 'Bike parking',
      'kind': 'vehicle_parking',
      'location': {'lat': 12.9777, 'lon': 80.2212},
      'radius_m': 150.0,
      'run_ids': ['replay-michaung'],
    });
    expect(view.runIds, ['replay-michaung']);
    expect(view.place.segmentIds, ['27480309-1']);
    expect(view.place.kind, SavedPlaceKind.VEHICLE_PARKING);
  });
}
