const NAMED: Record<string, string> = { 'replay-michaung': 'Cyclone Michaung' }

export const isReplay = (runId: string) => runId.startsWith('replay-')

export function runTag(runId: string): 'Replay' | 'Live' {
  return isReplay(runId) ? 'Replay' : 'Live'
}

/** A Run's display name: "Cyclone Michaung", "Live storm", or the title-cased Replay name. */
export function runName(runId: string): string {
  if (NAMED[runId]) return NAMED[runId]
  if (!isReplay(runId)) return 'Live storm'
  return runId
    .slice('replay-'.length)
    .split('-')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}
