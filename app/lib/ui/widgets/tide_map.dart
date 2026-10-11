import 'dart:math' show Point;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:maplibre_gl/maplibre_gl.dart';

import '../../contracts/nimbus.dart';
import '../theme/tide_colors.dart';
import 'map_layers.dart';

/// False in widget tests, where a MapLibre platform view can't render: the
/// map is then a plain Deep tide background.
final mapEnabledProvider = Provider<bool>((ref) => true);

/// Velachery, the demo Ward.
final velachery = GeoPoint(lat: 12.975, lon: 80.219);

const _style = 'assets/map/tide_style.json';
const _hazardRed = '#FF4D4D';

/// The Deep tide map: OpenFreeMap streets in the dark style, with the
/// Segments by band, observed water, Hazards and their no-go rings, a route
/// and labelled points on top. Sources update when the inputs change.
class TideMap extends ConsumerStatefulWidget {
  const TideMap({
    super.key,
    required this.segments,
    required this.risk,
    this.hazards = const [],
    this.route,
    this.focus,
    this.zoom = 15,
    this.emphasise,
    this.points = const {},
    this.waterMarks = const [],
    this.onTap,
    this.interactive = true,
  });

  final List<Segment> segments;
  final Map<String, SegmentRisk> risk;
  final List<Hazard> hazards;
  final LineString? route;
  final GeoPoint? focus;
  final double zoom;

  /// Only these Segments at full strength; the rest are dimmed.
  final Set<String>? emphasise;

  /// Labelled pins, e.g. {'A': origin, 'B': destination}.
  final Map<String, GeoPoint> points;

  /// Where Readings were observed.
  final List<GeoPoint> waterMarks;

  final ValueChanged<GeoPoint>? onTap;
  final bool interactive;

  @override
  ConsumerState<TideMap> createState() => _TideMapState();
}

class _TideMapState extends ConsumerState<TideMap> {
  MapLibreMapController? _map;
  var _ready = false;

  @override
  void didUpdateWidget(TideMap old) {
    super.didUpdateWidget(old);
    if (!_ready) return;
    _pushSources();
    final f = widget.focus;
    if (f != null && (f.lat != old.focus?.lat || f.lon != old.focus?.lon || widget.zoom != old.zoom)) {
      _map?.animateCamera(CameraUpdate.newLatLngZoom(LatLng(f.lat, f.lon), widget.zoom));
    }
  }

  Map<String, Map<String, dynamic>> _sources() => {
        'segments': segmentsGeoJson(widget.segments, widget.risk, emphasise: widget.emphasise),
        'hazards': hazardsGeoJson(widget.hazards),
        'hazard-rings': hazardRingsGeoJson(widget.hazards),
        'route': lineGeoJson(widget.route),
        'points': pointsGeoJson(widget.points),
        'water-marks': pointsGeoJson({for (var i = 0; i < widget.waterMarks.length; i++) '$i': widget.waterMarks[i]}),
      };

  Future<void> _pushSources() async {
    final map = _map;
    if (map == null) return;
    for (final MapEntry(:key, :value) in _sources().entries) {
      await map.setGeoJsonSource(key, value);
    }
  }

  Future<void> _addLayers() async {
    final map = _map;
    if (map == null) return;
    for (final MapEntry(:key, :value) in _sources().entries) {
      await map.addGeoJsonSource(key, value);
    }
    final dim = ['case', ['get', 'dim'], 0.35, 1.0];
    final flooded = ['==', ['get', 'band'], 'flooded'];
    final notFlooded = ['!=', ['get', 'band'], 'flooded'];

    await map.addLineLayer('segments', 'seg-casing',
        LineLayerProperties(lineColor: hexColor(TideColors.mapRoad), lineWidth: 9, lineCap: 'round', lineJoin: 'round'));
    await map.addLineLayer(
        'segments',
        'seg-band',
        LineLayerProperties(
          lineColor: ['get', 'color'],
          lineWidth: ['case', ['==', ['get', 'band'], 'likely'], 4.5, 3.5],
          lineOpacity: dim,
          lineCap: 'round',
          lineJoin: 'round',
        ),
        filter: notFlooded);
    await map.addLineLayer(
        'segments',
        'seg-flooded-halo',
        LineLayerProperties(
            lineColor: hexColor(TideColors.water), lineWidth: 16, lineOpacity: 0.25, lineBlur: 3, lineCap: 'round'),
        filter: flooded);
    await map.addLineLayer(
        'segments',
        'seg-flooded',
        LineLayerProperties(lineColor: hexColor(TideColors.water), lineWidth: 8, lineOpacity: dim, lineCap: 'round'),
        filter: flooded);
    await map.addLineLayer('route', 'route-glow',
        LineLayerProperties(lineColor: hexColor(TideColors.accent), lineWidth: 14, lineOpacity: 0.22, lineBlur: 2, lineCap: 'round', lineJoin: 'round'));
    await map.addLineLayer('route', 'route-line',
        LineLayerProperties(lineColor: hexColor(TideColors.accent), lineWidth: 5.5, lineCap: 'round', lineJoin: 'round'));
    await map.addLineLayer('hazard-rings', 'hazard-ring',
        const LineLayerProperties(lineColor: _hazardRed, lineWidth: 1.6, lineDasharray: [2, 2], lineOpacity: 0.9));
    await map.addCircleLayer('hazards', 'hazard-dot',
        const CircleLayerProperties(circleColor: _hazardRed, circleRadius: 4.5, circleStrokeColor: '#FFFFFF', circleStrokeWidth: 1.2));
    await map.addCircleLayer(
        'water-marks',
        'water-mark',
        CircleLayerProperties(
            circleColor: hexColor(TideColors.water), circleRadius: 5, circleStrokeColor: '#FFFFFF', circleStrokeWidth: 1.5));
    await map.addCircleLayer(
        'points',
        'point-dot',
        CircleLayerProperties(
            circleColor: '#FFFFFF', circleRadius: 9, circleStrokeColor: hexColor(TideColors.accent), circleStrokeWidth: 2.5));
    await map.addSymbolLayer(
        'points',
        'point-label',
        SymbolLayerProperties(
          textField: ['get', 'label'],
          textFont: ['Noto Sans Regular'],
          textSize: 11,
          textColor: hexColor(TideColors.deep),
          textAllowOverlap: true,
          textIgnorePlacement: true,
        ));
    _ready = true;
    if (mounted) _pushSources();
  }

  @override
  Widget build(BuildContext context) {
    if (!ref.watch(mapEnabledProvider)) return const ColoredBox(color: TideColors.mapBg, child: SizedBox.expand());
    final f = widget.focus ?? velachery;
    return MapLibreMap(
      styleString: _style,
      initialCameraPosition: CameraPosition(target: LatLng(f.lat, f.lon), zoom: widget.zoom),
      onMapCreated: (c) => _map = c,
      onStyleLoadedCallback: _addLayers,
      onMapClick: (Point<double> _, LatLng at) => widget.onTap?.call(GeoPoint(lat: at.latitude, lon: at.longitude)),
      compassEnabled: false,
      rotateGesturesEnabled: false,
      tiltGesturesEnabled: false,
      scrollGesturesEnabled: widget.interactive,
      zoomGesturesEnabled: widget.interactive,
      attributionButtonPosition: AttributionButtonPosition.bottomLeft,
      attributionButtonColor: TideColors.muted,
    );
  }
}
