import type { FeatureCollection } from 'geojson'
import type { ExpressionSpecification, GeoJSONSource, Map as MapLibreMap } from 'maplibre-gl'
import { BAND_COLOR, LIKELY_FROM, WATCH_FROM } from '../../domain/bands'
import type { PolygonFeature, SegmentCollection } from '../../domain/geo'

export type LayerKey = 'risk' | 'readings' | 'hazards' | 'resources' | 'sos'
export type NoGoCollection = { type: 'FeatureCollection'; features: PolygonFeature[] }
export type NimbusLayerData = { segments: SegmentCollection; nogo: NoGoCollection }

export const EMPTY_DATA: NimbusLayerData = {
  segments: { type: 'FeatureCollection', features: [] },
  nogo: { type: 'FeatureCollection', features: [] },
}

const byScore: ExpressionSpecification = [
  'step',
  ['get', 'score'],
  BAND_COLOR.low,
  WATCH_FROM,
  BAND_COLOR.watch,
  LIKELY_FROM,
  BAND_COLOR.likely,
]

/** Flooded is cyan only while Readings are shown; otherwise the score decides. */
function segmentColour(showReadings: boolean): ExpressionSpecification {
  return [
    'match',
    ['get', 'band'],
    'flooded',
    showReadings ? BAND_COLOR.flooded : byScore,
    'likely',
    BAND_COLOR.likely,
    'watch',
    BAND_COLOR.watch,
    BAND_COLOR.low,
  ]
}

export function addNimbusLayers(map: MapLibreMap, data: NimbusLayerData): void {
  map.addSource('segments', { type: 'geojson', data: data.segments as FeatureCollection })
  map.addSource('nogo', { type: 'geojson', data: data.nogo as FeatureCollection })
  map.addLayer({ id: 'nogo-fill', type: 'fill', source: 'nogo', paint: { 'fill-color': BAND_COLOR.likely, 'fill-opacity': 0.08 } })
  map.addLayer({
    id: 'nogo-line',
    type: 'line',
    source: 'nogo',
    paint: { 'line-color': BAND_COLOR.likely, 'line-width': 1.2, 'line-dasharray': [3, 2] },
  })
  map.addLayer({
    id: 'seg-case',
    type: 'line',
    source: 'segments',
    layout: { 'line-cap': 'round', 'line-join': 'round' },
    paint: { 'line-color': '#0A1F44', 'line-width': ['interpolate', ['linear'], ['zoom'], 14, 6, 18, 16] },
  })
  map.addLayer({
    id: 'seg',
    type: 'line',
    source: 'segments',
    layout: { 'line-cap': 'round', 'line-join': 'round', 'line-sort-key': ['get', 'score'] },
    paint: {
      'line-color': segmentColour(true),
      'line-opacity': ['match', ['get', 'band'], 'low', 0.45, 1],
      'line-width': ['interpolate', ['linear'], ['zoom'], 14, 3, 18, 10],
    },
  })
}

export function updateNimbusData(map: MapLibreMap, data: NimbusLayerData): void {
  ;(map.getSource('segments') as GeoJSONSource | undefined)?.setData(data.segments as FeatureCollection)
  ;(map.getSource('nogo') as GeoJSONSource | undefined)?.setData(data.nogo as FeatureCollection)
}

const LAYERS: Partial<Record<LayerKey, string[]>> = {
  risk: ['seg', 'seg-case'],
  hazards: ['nogo-fill', 'nogo-line'],
}

/** Map-drawn layers only; pins for resources, SOS and hazards are HTML markers handled by MapView. */
export function setLayerVisible(map: MapLibreMap, key: LayerKey, visible: boolean): void {
  if (key === 'readings') {
    if (map.getLayer('seg')) map.setPaintProperty('seg', 'line-color', segmentColour(visible))
    return
  }
  for (const id of LAYERS[key] ?? []) {
    if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', visible ? 'visible' : 'none')
  }
}
