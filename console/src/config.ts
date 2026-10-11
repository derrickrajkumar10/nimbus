export type Config = {
  /** Console HTTP API base URL. Null runs the console on contracts/fixtures. */
  apiUrl: string | null
  /** Citizen HTTP API base URL, used for `GET /segments`. */
  citizenApiUrl: string | null
  /** Sent as `decided_by` until Cognito (#19) gives real identities. */
  officerId: string
  officerName: string
  wardName: string
  runs: string[]
  runId: string
}

type Env = Record<string, string | undefined>

const value = (v: string | undefined) => (v && v.trim() ? v.trim() : null)
const url = (v: string | undefined) => value(v)?.replace(/\/+$/, '') ?? null

export function readConfig(env: Env, search: string): Config {
  const runs = value(env.VITE_RUNS)
    ?.split(',')
    .map((r) => r.trim())
    .filter(Boolean) ?? ['replay-michaung', 'live']
  return {
    apiUrl: url(env.VITE_NIMBUS_API),
    citizenApiUrl: url(env.VITE_CITIZEN_API),
    officerId: value(env.VITE_OFFICER_ID) ?? 'officer-1',
    officerName: value(env.VITE_OFFICER_NAME) ?? 'K. Priya',
    wardName: value(env.VITE_WARD_NAME) ?? 'Velachery',
    runs,
    runId: value(new URLSearchParams(search).get('run') ?? undefined) ?? runs[0],
  }
}
