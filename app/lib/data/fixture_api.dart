import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

import '../contracts/nimbus.dart';
import '../domain/geo.dart';
import '../domain/place_view.dart';
import 'api_exception.dart';
import 'ids.dart';
import 'nimbus_api.dart';

/// The citizen API answered from `assets/fixtures/`, with a short delay so
/// loading states show. The fixture scene is the `replay-michaung` Run, so
/// `live` lists are empty. Saved Places live in memory.
class FixtureNimbusApi implements NimbusApi {
  FixtureNimbusApi(this.bundle, {this.delay = const Duration(milliseconds: 600)});

  final AssetBundle bundle;
  final Duration delay;

  /// How long the "Verifier" takes before a new Report's Reading appears.
  static const verifyTime = Duration(seconds: 3);
  static const maxPlaces = 20;

  final _places = <String, PlaceView>{};
  final _verified = <String>{};
  final _json = <String, List<Map<String, dynamic>>>{};

  Future<List<Map<String, dynamic>>> _load(String name) async =>
      _json[name] ??= (jsonDecode(await bundle.loadString('assets/fixtures/$name')) as List)
          .cast<Map<String, dynamic>>();

  Future<List<T>> _rows<T>(String name, T Function(Map<String, dynamic>) fromJson, {String? runId}) async {
    await Future<void>.delayed(delay);
    return [
      for (final j in await _load(name))
        if (runId == null || j['run_id'] == runId) fromJson(j),
    ];
  }

  /// The scene's storm time, used where the API would stamp the Run's time.
  Future<DateTime> _sceneTime() async => DateTime.parse((await _load('risk.json')).first['sim_time'] as String);

  @override
  Future<List<Segment>> segments() => _rows('segments.json', Segment.fromJson);

  @override
  Future<List<SegmentRisk>> risk(String runId) => _rows('risk.json', SegmentRisk.fromJson, runId: runId);

  @override
  Future<List<Reading>> readings(String runId, {String? reportId}) async {
    final all = await _rows('readings.json', Reading.fromJson, runId: runId);
    if (reportId == null) return all;
    // A new Report's Reading is the scene's knee-deep one, once "verified".
    return _verified.contains(reportId) ? all.take(1).toList() : const [];
  }

  @override
  Future<List<Hazard>> hazards(String runId) => _rows('hazards.json', Hazard.fromJson, runId: runId);

  @override
  Future<void> registerDevice(String fcmToken, String language) async {
    await Future<void>.delayed(delay);
    debugPrint('fixture POST /devices language=$language token=${fcmToken.length} chars');
  }

  @override
  Future<List<PlaceView>> savedPlaces() async {
    await Future<void>.delayed(delay);
    return _places.values.toList();
  }

  @override
  Future<PlaceView> putPlace(
    String placeId, {
    required String label,
    required SavedPlaceKind kind,
    required GeoPoint location,
    double? radiusM,
    required List<String> runIds,
  }) async {
    if (!_places.containsKey(placeId) && _places.length >= maxPlaces) {
      throw const ApiException(409, ApiException.tooManyPlaces, 'At most 20 places per install');
    }
    final segments = await this.segments();
    final view = PlaceView(
      place: SavedPlace(
        deviceId: 'fixture',
        kind: kind,
        label: label,
        location: location,
        placeId: placeId,
        radiusM: radiusM,
        segmentIds: segmentsNear(location, radiusM ?? 150, segments),
      ),
      runIds: runIds,
    );
    return _places[placeId] = view;
  }

  @override
  Future<void> deletePlace(String placeId) async {
    await Future<void>.delayed(delay);
    _places.remove(placeId);
  }

  @override
  Future<UploadTicket> uploadUrl(String runId) async {
    await Future<void>.delayed(delay);
    final id = recordId('rp');
    return UploadTicket(
      reportId: id,
      photoKey: 'reports/$runId/$id.jpg',
      uploadUrl: Uri.parse('https://fixture.invalid/reports/$runId/$id.jpg'),
      headers: const {'content-type': 'image/jpeg'},
    );
  }

  @override
  Future<void> uploadPhoto(UploadTicket t, Uint8List jpeg) => Future<void>.delayed(delay);

  @override
  Future<Report> createReport({
    required String reportId,
    required String runId,
    required GeoPoint location,
    String? note,
  }) async {
    await Future<void>.delayed(delay);
    Timer(verifyTime, () => _verified.add(reportId));
    return Report(
      capturedAt: await _sceneTime(),
      location: location,
      note: note,
      photoKey: 'reports/$runId/$reportId.jpg',
      reportId: reportId,
      reporterId: 'fixture',
      runId: runId,
      source: ReportSource.APP,
    );
  }

  @override
  Future<Sos> createSos({
    required String sosId,
    required String runId,
    required GeoPoint location,
    required int peopleCount,
    required VulnerabilityFlags flags,
  }) async {
    await Future<void>.delayed(delay);
    return Sos(
      createdAt: await _sceneTime(),
      flags: flags,
      location: location,
      peopleCount: peopleCount,
      reporterId: 'fixture',
      runId: runId,
      sosId: sosId,
    );
  }

  @override
  Future<RouteResponse> route(RouteRequest req) async {
    final routes = await _rows('routes.json', RouteResponse.fromJson);
    // The scene: a detour for the two-wheeler (and the ambulance, which can
    // pass knee-deep water), and no safe route for a car.
    return req.vehicle == VehicleType.CAR ? routes[1] : routes[0];
  }
}
