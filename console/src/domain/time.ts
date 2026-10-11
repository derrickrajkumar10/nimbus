// Storm times are shown in IST. Ward offices run on IST and India has no DST,
// so a fixed +05:30 shift is exact and avoids locale quirks.
const IST_OFFSET_MS = (5 * 60 + 30) * 60 * 1000
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

const pad = (n: number) => String(n).padStart(2, '0')

function ist(iso: string): Date {
  return new Date(Date.parse(iso) + IST_OFFSET_MS)
}

/** The latest instant among `times`, returned as given, or null when empty. */
export function stormClock(times: string[]): string | null {
  let best: string | null = null
  let bestMs = -Infinity
  for (const t of times) {
    const ms = Date.parse(t)
    if (ms > bestMs) {
      bestMs = ms
      best = t
    }
  }
  return best
}

export function hhmm(iso: string): string {
  const d = ist(iso)
  return `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`
}

export function formatClock(iso: string): { time: string; date: string } {
  const d = ist(iso)
  return {
    time: hhmm(iso),
    date: `${DAYS[d.getUTCDay()]} ${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`,
  }
}

/** Whole minutes from `fromIso` to `toIso`, never negative. */
export function minutesBetween(fromIso: string, toIso: string): number {
  return Math.max(0, Math.floor((Date.parse(toIso) - Date.parse(fromIso)) / 60000))
}
