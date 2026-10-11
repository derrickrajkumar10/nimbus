import type { RainPoint, ReplaySpeed } from '../data/source'
import { formatClock, hhmm } from './time'

export type RainGeometry = {
  line: string
  area: string
  nowX: number | null
  nowY: number | null
  nowMm: number | null
  ticks: { x: number; label: string; anchor: 'start' | 'middle' | 'end' }[]
}

const TOP = 14
const BOTTOM_GAP = 16
const HOUR_MS = 3600000

const dayMonth = (iso: string) => formatClock(iso).date.split(' ').slice(1, 3).join(' ')

/** SVG paths for the storm's hourly rain, and where the storm clock sits on it. */
export function rainGeometry(points: RainPoint[], nowIso: string | null, width: number, height: number): RainGeometry {
  if (points.length === 0) return { line: '', area: '', nowX: null, nowY: null, nowMm: null, ticks: [] }
  const base = height - BOTTOM_GAP
  const max = Math.max(1, ...points.map((p) => p.mm))
  const x = (i: number) => (points.length === 1 ? 0 : (i / (points.length - 1)) * width)
  const y = (mm: number) => base - (mm / max) * (base - TOP)
  const r = (n: number) => Math.round(n * 10) / 10

  const line = points.map((p, i) => `${i ? 'L' : 'M'}${r(x(i))},${r(y(p.mm))}`).join(' ')
  const area = `${line} L${r(x(points.length - 1))},${base} L0,${base} Z`

  const now = nowIso ? Date.parse(nowIso) : NaN
  const i = points.findIndex((p) => {
    const t = Date.parse(p.time)
    return now >= t && now < t + HOUR_MS
  })

  const last = points.length - 1
  const ticks: RainGeometry['ticks'] = [{ x: 0, label: `${hhmm(points[0].time)} · ${dayMonth(points[0].time)}`, anchor: 'start' }]
  points.forEach((p, j) => {
    const h = hhmm(p.time)
    if (j > 0 && j < last && (h === '00:00' || h === '06:00')) ticks.push({ x: x(j), label: h, anchor: 'middle' })
  })
  if (last > 0) ticks.push({ x: x(last), label: `${hhmm(points[last].time)} · ${dayMonth(points[last].time)}`, anchor: 'end' })

  return {
    line,
    area,
    nowX: i === -1 ? null : x(i),
    nowY: i === -1 ? null : y(points[i].mm),
    nowMm: i === -1 ? null : points[i].mm,
    ticks,
  }
}

export const SPEEDS: ReplaySpeed[] = [15, 30, 60, 120]

export function nextSpeed(s: ReplaySpeed): ReplaySpeed {
  return SPEEDS[(SPEEDS.indexOf(s) + 1) % SPEEDS.length]
}
