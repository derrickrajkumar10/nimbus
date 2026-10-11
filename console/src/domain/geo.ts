import type { GeoPoint, RiskBand, Segment, SegmentRisk } from '@contracts/generated/ts/nimbus'

export type SegmentProps = { segment_id: string; street: string; band: RiskBand; score: number }

type LngLat = [number, number]
type LineFeature = { type: 'Feature'; geometry: { type: 'LineString'; coordinates: LngLat[] }; properties: SegmentProps }
export type SegmentCollection = { type: 'FeatureCollection'; features: LineFeature[] }
export type PolygonFeature = { type: 'Feature'; geometry: { type: 'Polygon'; coordinates: LngLat[][] }; properties: Record<string, never> }

const M_PER_DEG_LAT = 110540
const M_PER_DEG_LON = 111320

export function streetName(s: Segment): string {
  return s.street_name ?? 'Unnamed road'
}

export function segmentsToGeoJSON(segments: Segment[], risk: SegmentRisk[]): SegmentCollection {
  const byId = new Map(risk.map((r) => [r.segment_id, r]))
  return {
    type: 'FeatureCollection',
    features: segments.map((s) => {
      const r = byId.get(s.segment_id)
      return {
        type: 'Feature',
        geometry: { type: 'LineString', coordinates: s.geometry.coordinates.map(([x, y]) => [x, y] as LngLat) },
        properties: { segment_id: s.segment_id, street: streetName(s), band: r?.band ?? 'low', score: r?.score ?? 0 },
      }
    }),
  }
}

/** Squared distance in metres from p to the line piece a–b, on a local flat projection. */
function pieceDistance2(p: GeoPoint, a: number[], b: number[]): number {
  const k = Math.cos((p.lat * Math.PI) / 180) * M_PER_DEG_LON
  const ax = (a[0] - p.lon) * k
  const ay = (a[1] - p.lat) * M_PER_DEG_LAT
  const bx = (b[0] - p.lon) * k
  const by = (b[1] - p.lat) * M_PER_DEG_LAT
  const dx = bx - ax
  const dy = by - ay
  const len2 = dx * dx + dy * dy
  const t = len2 === 0 ? 0 : Math.max(0, Math.min(1, -(ax * dx + ay * dy) / len2))
  const x = ax + t * dx
  const y = ay + t * dy
  return x * x + y * y
}

export function nearestSegment(p: GeoPoint, segments: Segment[]): Segment | null {
  let best: Segment | null = null
  let bestD = Infinity
  for (const s of segments) {
    const c = s.geometry.coordinates
    for (let i = 0; i < c.length - 1; i++) {
      const d = pieceDistance2(p, c[i], c[i + 1])
      if (d < bestD) {
        bestD = d
        best = s
      }
    }
  }
  return best
}

export function segmentMidpoint(s: Segment): LngLat {
  const c = s.geometry.coordinates[Math.floor(s.geometry.coordinates.length / 2)]
  return [c[0], c[1]]
}

export function circlePolygon(c: GeoPoint, radiusM: number, steps = 48): PolygonFeature {
  const ring: LngLat[] = []
  const k = Math.cos((c.lat * Math.PI) / 180) * M_PER_DEG_LON
  for (let i = 0; i < steps; i++) {
    const a = (i / steps) * Math.PI * 2
    ring.push([c.lon + (radiusM / k) * Math.cos(a), c.lat + (radiusM / M_PER_DEG_LAT) * Math.sin(a)])
  }
  ring.push(ring[0])
  return { type: 'Feature', geometry: { type: 'Polygon', coordinates: [ring] }, properties: {} }
}
