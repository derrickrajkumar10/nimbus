import 'dart:typed_data';

import '../contracts/nimbus.dart';
import '../domain/place_view.dart';

/// A signed upload for one Report's photo, from `POST /reports/upload-url`.
class UploadTicket {
  const UploadTicket({
    required this.reportId,
    required this.photoKey,
    required this.uploadUrl,
    required this.headers,
  });

  final String reportId;
  final String photoKey;
  final Uri uploadUrl;
  final Map<String, String> headers;
}

/// Everything the app asks of the citizen API. [HttpNimbusApi] talks to it;
/// [FixtureNimbusApi] answers from bundled fixtures. Errors are ApiException.
abstract class NimbusApi {
  Future<List<Segment>> segments();
  Future<List<SegmentRisk>> risk(String runId);
  Future<List<Reading>> readings(String runId, {String? reportId});
  Future<List<Hazard>> hazards(String runId);
  Future<void> registerDevice(String fcmToken, String language);
  Future<List<PlaceView>> savedPlaces();
  Future<PlaceView> putPlace(
    String placeId, {
    required String label,
    required SavedPlaceKind kind,
    required GeoPoint location,
    double? radiusM,
    required List<String> runIds,
  });
  Future<void> deletePlace(String placeId);
  Future<UploadTicket> uploadUrl(String runId);
  Future<void> uploadPhoto(UploadTicket t, Uint8List jpeg);
  Future<Report> createReport({
    required String reportId,
    required String runId,
    required GeoPoint location,
    String? note,
  });
  Future<Sos> createSos({
    required String sosId,
    required String runId,
    required GeoPoint location,
    required int peopleCount,
    required VulnerabilityFlags flags,
  });
  Future<RouteResponse> route(RouteRequest req);
}

/// Request body for flags: unset flags are left out rather than sent as null.
Map<String, dynamic> flagsJson(VulnerabilityFlags f) => f.toJson()..removeWhere((_, v) => v == null);
