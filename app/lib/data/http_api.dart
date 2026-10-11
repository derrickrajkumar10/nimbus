import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;

import '../contracts/nimbus.dart';
import '../domain/place_view.dart';
import 'api_exception.dart';
import 'fixture_api.dart';
import 'nimbus_api.dart';

/// The citizen API (api/README.md, "Citizen API"). Reads carry `run_id` as a
/// query parameter; install routes carry `X-Install-Id`.
class HttpNimbusApi implements NimbusApi {
  HttpNimbusApi(this.base, this.installId, {http.Client? client, FixtureNimbusApi? fixtures})
      : _client = client ?? http.Client(),
        _fixtures = fixtures ?? FixtureNimbusApi(rootBundle, delay: Duration.zero);

  final Uri base;
  final String installId;
  final http.Client _client;

  /// Answers `hazards` until the API has `GET /hazards` (#58).
  final FixtureNimbusApi _fixtures;

  static const timeout = Duration(seconds: 10);

  Uri _uri(String path, [Map<String, String>? query]) {
    final prefix = base.path.endsWith('/') ? base.path.substring(0, base.path.length - 1) : base.path;
    return base.replace(path: '$prefix$path', queryParameters: query);
  }

  Map<String, String> _headers({bool install = false, bool body = false}) => {
        if (install) 'X-Install-Id': installId,
        if (body) 'content-type': 'application/json',
      };

  Future<http.Response> _send(Future<http.Response> Function() request) async {
    final http.Response res;
    try {
      res = await request().timeout(timeout);
    } on SocketException catch (e) {
      throw ApiException.offline(e.message);
    } on TimeoutException {
      throw const ApiException.offline('Timed out');
    } on http.ClientException catch (e) {
      throw ApiException.offline(e.message);
    }
    if (res.statusCode >= 200 && res.statusCode < 300) return res;
    throw _error(res);
  }

  static ApiException _error(http.Response res) {
    try {
      final body = jsonDecode(utf8.decode(res.bodyBytes));
      if (body is Map<String, dynamic>) {
        return ApiException(
          res.statusCode,
          (body['error'] as String?) ?? 'http_${res.statusCode}',
          (body['message'] as String?) ?? '',
        );
      }
    } on FormatException {
      // Not JSON (a gateway error page); fall through.
    }
    return ApiException(res.statusCode, 'http_${res.statusCode}');
  }

  static dynamic _decode(http.Response res) => jsonDecode(utf8.decode(res.bodyBytes));

  Future<dynamic> _get(String path, {Map<String, String>? query, bool install = false}) async =>
      _decode(await _send(() => _client.get(_uri(path, query), headers: _headers(install: install))));

  Future<dynamic> _write(String method, String path, Object? body) async {
    final req = http.Request(method, _uri(path))
      ..headers.addAll(_headers(install: true, body: body != null));
    if (body != null) req.body = jsonEncode(body);
    return _decode(await _send(() async => http.Response.fromStream(await _client.send(req))));
  }

  static List<T> _list<T>(dynamic json, T Function(Map<String, dynamic>) fromJson) =>
      [for (final j in json as List) fromJson(j as Map<String, dynamic>)];

  @override
  Future<List<Segment>> segments() async => _list(await _get('/segments'), Segment.fromJson);

  @override
  Future<List<SegmentRisk>> risk(String runId) async =>
      _list(await _get('/risk', query: {'run_id': runId}), SegmentRisk.fromJson);

  @override
  Future<List<Reading>> readings(String runId, {String? reportId}) async => _list(
        await _get('/readings', query: {'run_id': runId, 'report_id': ?reportId}),
        Reading.fromJson,
      );

  @override
  Future<List<Hazard>> hazards(String runId) async {
    try {
      return _list(await _get('/hazards', query: {'run_id': runId}), Hazard.fromJson);
    } on ApiException catch (e) {
      // No GET /hazards on the citizen API yet (#58). Any 404, since API
      // Gateway's own 404 has no `error` code.
      if (e.status == 404) return _fixtures.hazards(runId);
      rethrow;
    }
  }

  @override
  Future<void> registerDevice(String fcmToken, String language) =>
      _write('POST', '/devices', {'fcm_token': fcmToken, 'language': language});

  @override
  Future<List<PlaceView>> savedPlaces() async =>
      _list(await _get('/saved-places', install: true), PlaceView.fromJson);

  @override
  Future<PlaceView> putPlace(
    String placeId, {
    required String label,
    required SavedPlaceKind kind,
    required GeoPoint location,
    double? radiusM,
    required List<String> runIds,
  }) async =>
      PlaceView.fromJson(await _write('PUT', '/saved-places/${Uri.encodeComponent(placeId)}', {
        'label': label,
        'kind': savedPlaceKindValues.reverse[kind],
        'location': location.toJson(),
        'radius_m': ?radiusM,
        'run_ids': runIds,
      }) as Map<String, dynamic>);

  @override
  Future<void> deletePlace(String placeId) =>
      _write('DELETE', '/saved-places/${Uri.encodeComponent(placeId)}', null);

  @override
  Future<UploadTicket> uploadUrl(String runId) async {
    final j = await _write('POST', '/reports/upload-url', {'run_id': runId}) as Map<String, dynamic>;
    return UploadTicket(
      reportId: j['report_id'] as String,
      photoKey: j['photo_key'] as String,
      uploadUrl: Uri.parse(j['upload_url'] as String),
      headers: Map<String, String>.from(j['headers'] as Map? ?? const {}),
    );
  }

  @override
  Future<void> uploadPhoto(UploadTicket t, Uint8List jpeg) =>
      _send(() => _client.put(t.uploadUrl, headers: t.headers, body: jpeg));

  @override
  Future<Report> createReport({
    required String reportId,
    required String runId,
    required GeoPoint location,
    String? note,
  }) async =>
      Report.fromJson(await _write('POST', '/reports', {
        'report_id': reportId,
        'run_id': runId,
        'location': location.toJson(),
        'note': ?note,
      }) as Map<String, dynamic>);

  @override
  Future<Sos> createSos({
    required String sosId,
    required String runId,
    required GeoPoint location,
    required int peopleCount,
    required VulnerabilityFlags flags,
  }) async =>
      Sos.fromJson(await _write('POST', '/sos', {
        'sos_id': sosId,
        'run_id': runId,
        'location': location.toJson(),
        'people_count': peopleCount,
        'flags': flagsJson(flags),
      }) as Map<String, dynamic>);

  @override
  Future<RouteResponse> route(RouteRequest req) async =>
      RouteResponse.fromJson(await _write('POST', '/routes', req.toJson()) as Map<String, dynamic>);
}
