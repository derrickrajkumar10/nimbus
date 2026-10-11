import { MICHAUNG_RAIN } from '../data/fixtureScene'
import { SPEEDS, nextSpeed, rainGeometry } from './rain'

test('rainGeometry places now at 02:00 with 3.2 mm/h', () => {
  const g = rainGeometry(MICHAUNG_RAIN, '2023-12-04T02:00:00+05:30', 900, 62)
  expect(g.nowMm).toBe(3.2)
  expect(g.nowX).toBeCloseTo((900 * 8) / 18, 5)
  expect(g.nowY).toBeGreaterThan(14)
  expect(g.nowY).toBeLessThan(62 - 16)
})

test('rainGeometry finds the hour that contains the clock', () => {
  expect(rainGeometry(MICHAUNG_RAIN, '2023-12-04T02:45:00+05:30', 900, 62).nowMm).toBe(3.2)
})

test('rainGeometry with a clock outside the series has no playhead', () => {
  const g = rainGeometry(MICHAUNG_RAIN, '2023-12-05T02:00:00+05:30', 900, 62)
  expect(g).toMatchObject({ nowX: null, nowY: null, nowMm: null })
  expect(rainGeometry(MICHAUNG_RAIN, null, 900, 62).nowX).toBeNull()
})

test('rainGeometry ticks', () => {
  const g = rainGeometry(MICHAUNG_RAIN, null, 900, 62)
  expect(g.ticks.map((t) => t.label)).toEqual(['18:00 · 3 Dec', '00:00', '06:00', '12:00 · 4 Dec'])
  expect(g.ticks.map((t) => t.anchor)).toEqual(['start', 'middle', 'middle', 'end'])
  expect(g.ticks[3].x).toBe(900)
})

test('rainGeometry draws a closed area under the line', () => {
  const g = rainGeometry(MICHAUNG_RAIN, null, 900, 62)
  expect(g.line.startsWith('M0,')).toBe(true)
  expect(g.area.endsWith('Z')).toBe(true)
  expect(rainGeometry([], null, 900, 62)).toMatchObject({ line: '', area: '', ticks: [] })
})

test('nextSpeed cycles 120 → 15', () => {
  expect(SPEEDS).toEqual([15, 30, 60, 120])
  expect(nextSpeed(60)).toBe(120)
  expect(nextSpeed(120)).toBe(15)
})
