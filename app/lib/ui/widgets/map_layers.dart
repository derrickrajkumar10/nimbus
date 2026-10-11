import 'dart:math' as math;

import 'package:flutter/painting.dart';

import '../../contracts/nimbus.dart';
import '../theme/tide_colors.dart';

/// `#rrggbb` for a MapLibre paint property.
String hexColor(Color c) =>
    '#${(c.toARGB32() & 0xFFFFFF).toRadixString(16).padLeft(6, '0')}';

/// The Segments as GeoJSON lines with their band and colour. A Segment with no
/// risk row has band `none`. With [emphasise], every other Segment is `dim`.
Map<String, dynamic> segmentsGeoJson(
  List<Segment> s,
  Map<String, SegmentRisk> risk, {
  Set<String>? emphasise,
}) =>
    {
      'type': 'FeatureCollection',
      'features': [
        for (final seg in s)
          {
            'type': 'Feature',
            'id': seg.segmentId,
            'geometry': {'type': 'LineString', 'coordinates': seg.geometry.coordinates},
            'properties': {
              'segment_id': seg.segmentId,
              'band': risk[seg.segmentId] == null ? 'none' : riskBandValues.reverse[risk[seg.segmentId]!.band],
              'color': hexColor(risk[seg.segmentId] == null ? TideColors.muted : bandColor(risk[seg.segmentId]!.band)),
              'dim': emphasise != null && !emphasise.contains(seg.segmentId),
            },
          },
      ],
    };

const _defaultNoGoM = 30.0;

/// Hazards as GeoJSON points with their no-go radius.
Map<String, dynamic> hazardsGeoJson(List<Hazard> h) => {
      'type': 'FeatureCollection',
      'features': [
        for (final hz in h)
          {
            'type': 'Feature',
            'id': hz.hazardId,
            'geometry': {
              'type': 'Point',
              'coordinates': [hz.location.lon, hz.location.lat],
            },
            'properties': {
              'hazard_id': hz.hazardId,
              'hazard_class': hazardClassValues.reverse[hz.hazardClass],
              'radius_m': hz.noGoRadiusM ?? _defaultNoGoM,
            },
          },
      ],
    };

/// Each Hazard's no-go ring as a closed line, so it can be drawn dashed
/// (MapLibre circles can't dash their stroke).
Map<String, dynamic> hazardRingsGeoJson(List<Hazard> h, {int points = 48}) => {
      'type': 'FeatureCollection',
      'features': [
        for (final hz in h)
          {
            'type': 'Feature',
            'geometry': {
              'type': 'LineString',
              'coordinates': _ring(hz.location, hz.noGoRadiusM ?? _defaultNoGoM, points),
            },
            'properties': {'hazard_id': hz.hazardId},
          },
      ],
    };

List<List<double>> _ring(GeoPoint c, double radiusM, int points) {
  const mPerDegLat = 111195.0;
  final mPerDegLon = mPerDegLat * math.cos(c.lat * math.pi / 180);
  final ring = [
    for (var i = 0; i < points; i++)
      () {
        final a = 2 * math.pi * i / points;
        return [c.lon + radiusM * math.sin(a) / mPerDegLon, c.lat + radiusM * math.cos(a) / mPerDegLat];
      }(),
  ];
  return [...ring, ring.first];
}

/// A route line, or nothing.
Map<String, dynamic> lineGeoJson(LineString? line) => {
      'type': 'FeatureCollection',
      'features': [
        if (line != null)
          {
            'type': 'Feature',
            'geometry': {'type': 'LineString', 'coordinates': line.coordinates},
            'properties': <String, dynamic>{},
          },
      ],
    };

/// Labelled points (route ends, a place's pin).
Map<String, dynamic> pointsGeoJson(Map<String, GeoPoint> labelled) => {
      'type': 'FeatureCollection',
      'features': [
        for (final MapEntry(:key, :value) in labelled.entries)
          {
            'type': 'Feature',
            'geometry': {
              'type': 'Point',
              'coordinates': [value.lon, value.lat],
            },
            'properties': {'label': key},
          },
      ],
    };
