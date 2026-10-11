import { circlePolygon, nearestSegment, segmentMidpoint, segmentsToGeoJSON, streetName } from './geo'
import { resources, risk, segments } from '../test/fixtures'

test('segmentsToGeoJSON joins risk', () => {
  const fc = segmentsToGeoJSON(segments, risk)
  expect(fc.features).toHaveLength(21)
  const flooded = fc.features.find((f) => f.properties.segment_id === '27480309-1')!
  expect(flooded.properties).toMatchObject({ band: 'flooded', score: 92, street: 'Velachery Main Road' })
  expect(flooded.geometry.type).toBe('LineString')
})

test('segmentsToGeoJSON treats a Segment without risk as low', () => {
  const fc = segmentsToGeoJSON(segments, [])
  expect(fc.features[0].properties).toMatchObject({ band: 'low', score: 0 })
})

test('streetName falls back', () => {
  expect(streetName({ ...segments[0], street_name: null })).toBe('Unnamed road')
  expect(streetName(segments[0])).toBe('Velachery Main Road')
})

test('nearestSegment finds the road Pump 2 stands on', () => {
  // Pump 2 sits on LIC Colony Main Road, 18 m from Velachery Main Road.
  const pump2 = resources.find((r) => r.resource_id === 'rs-pump-2')!
  expect(nearestSegment(pump2.location, segments)!.segment_id).toBe('30605099-3')
  const nearMainRoad = { lat: 12.9776, lon: 80.22121 }
  expect(streetName(nearestSegment(nearMainRoad, segments)!)).toBe('Velachery Main Road')
  expect(nearestSegment(pump2.location, [])).toBeNull()
})

test('segmentMidpoint returns the middle vertex as lon, lat', () => {
  const s = segments[0]
  const mid = s.geometry.coordinates[Math.floor(s.geometry.coordinates.length / 2)]
  expect(segmentMidpoint(s)).toEqual([mid[0], mid[1]])
})

test('circlePolygon closes the ring', () => {
  const ring = circlePolygon({ lat: 12.9777428, lon: 80.2212061 }, 30).geometry.coordinates[0]
  expect(ring).toHaveLength(49)
  expect(ring[0]).toEqual(ring[48])
})
