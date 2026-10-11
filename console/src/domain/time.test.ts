import { formatClock, hhmm, minutesBetween, stormClock } from './time'

test('stormClock returns the latest instant across offsets', () => {
  expect(stormClock(['2023-12-04T02:00:00+05:30', '2023-12-03T20:15:00Z'])).toBe('2023-12-04T02:00:00+05:30')
  expect(stormClock([])).toBeNull()
})

test('formatClock renders IST', () => {
  expect(formatClock('2023-12-03T20:30:00Z')).toEqual({ time: '02:00', date: 'Mon 4 Dec 2023' })
})

test('hhmm renders IST hours and minutes', () => {
  expect(hhmm('2023-12-04T01:55:00+05:30')).toBe('01:55')
})

test('minutesBetween floors and clamps', () => {
  expect(minutesBetween('2023-12-04T01:55:00+05:30', '2023-12-04T02:00:00+05:30')).toBe(5)
  expect(minutesBetween('2023-12-04T02:00:00+05:30', '2023-12-04T01:55:00+05:30')).toBe(0)
  expect(minutesBetween('2023-12-04T01:55:00+05:30', '2023-12-04T02:00:59+05:30')).toBe(5)
})
