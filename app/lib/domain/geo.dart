import 'dart:math' as math;

import '../contracts/nimbus.dart';

const _earthRadiusM = 6371008.8;

double _rad(double deg) => deg * math.pi / 180;

/// Great-circle distance in metres.
double distanceM(GeoPoint a, GeoPoint b) {
  final dLat = _rad(b.lat - a.lat), dLon = _rad(b.lon - a.lon);
  final h = math.pow(math.sin(dLat / 2), 2) +
      math.cos(_rad(a.lat)) * math.cos(_rad(b.lat)) * math.pow(math.sin(dLon / 2), 2);
  return 2 * _earthRadiusM * math.asin(math.sqrt(h));
}

/// Distance from [p] to the nearest point of a Segment's line. Each piece is
/// projected flat around [p], which is exact enough at street scale.
double distanceToLineM(GeoPoint p, LineString line) {
  final kx = _earthRadiusM * math.cos(_rad(p.lat)) * math.pi / 180;
  const ky = _earthRadiusM * math.pi / 180;
  final pts = [for (final c in line.coordinates) ((c[0] - p.lon) * kx, (c[1] - p.lat) * ky)];
  if (pts.length == 1) return math.sqrt(pts[0].$1 * pts[0].$1 + pts[0].$2 * pts[0].$2);
  var best = double.infinity;
  for (var i = 0; i + 1 < pts.length; i++) {
    final (ax, ay) = pts[i];
    final (bx, by) = pts[i + 1];
    final dx = bx - ax, dy = by - ay;
    final len2 = dx * dx + dy * dy;
    final t = len2 == 0 ? 0.0 : (-(ax * dx + ay * dy) / len2).clamp(0.0, 1.0);
    final cx = ax + t * dx, cy = ay + t * dy;
    best = math.min(best, math.sqrt(cx * cx + cy * cy));
  }
  return best;
}

/// The Segments a Saved Place covers, by the API's rule: every Segment whose
/// line passes within [radiusM], else the nearest one within 500 m.
List<String> segmentsNear(GeoPoint p, double radiusM, List<Segment> segments) {
  final within = <String>[];
  Segment? nearest;
  var nearestM = double.infinity;
  for (final s in segments) {
    final d = distanceToLineM(p, s.geometry);
    if (d <= radiusM) within.add(s.segmentId);
    if (d < nearestM) {
      nearestM = d;
      nearest = s;
    }
  }
  if (within.isNotEmpty) return within;
  return nearest != null && nearestM <= 500 ? [nearest.segmentId] : const [];
}
