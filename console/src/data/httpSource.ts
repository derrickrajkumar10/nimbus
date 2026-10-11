// The console HTTP API, exactly as documented in api/README.md (#8).
import type { Proposal } from '@contracts/generated/ts/nimbus'
import type { Config } from '../config'
import { MICHAUNG_RAIN } from './fixtureScene'
import { FIXTURE_RUN, FIXTURE_SEGMENTS, createLocalReplay } from './fixtureSource'
import {
  DecisionError,
  type ActivityPage,
  type CommanderClient,
  type DecisionErrorCode,
  type NimbusSource,
} from './source'

const DECISION_ERRORS: Record<number, DecisionErrorCode> = {
  404: 'proposal_not_found',
  409: 'already_decided',
  422: 'invalid',
  502: 'event_not_sent',
}

const unconfigured: CommanderClient = {
  ask() {
    throw new Error('commander not configured')
  },
}

export function createHttpSource(cfg: Config, fetchFn: typeof fetch = fetch): NimbusSource {
  const base = cfg.apiUrl ?? ''

  async function get<T>(path: string, params: Record<string, string | null | undefined>): Promise<T> {
    const q = new URLSearchParams()
    for (const [k, v] of Object.entries(params)) if (v != null) q.set(k, v)
    const res = await fetchFn(`${base}${path}?${q}`)
    if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`)
    return res.json() as Promise<T>
  }

  const byRun = <T>(path: string) => (runId: string) => get<T[]>(path, { run_id: runId })

  return {
    mode: 'http',
    runs: () => cfg.runs,

    async segments() {
      if (!cfg.citizenApiUrl) return structuredClone(FIXTURE_SEGMENTS)
      const res = await fetchFn(`${cfg.citizenApiUrl}/segments`)
      if (!res.ok) throw new Error(`GET /segments failed: ${res.status}`)
      return res.json()
    },

    risk: byRun('/risk'),
    readings: byRun('/readings'),
    hazards: byRun('/hazards'),
    resources: byRun('/resources'),
    sos: byRun('/sos'),
    proposals: byRun('/proposals'),

    activity: (runId, since) => get<ActivityPage>('/activity', { run_id: runId, limit: '500', since }),

    async decide(runId, proposalId, input) {
      const body = { run_id: runId, decision: input.decision, decided_by: input.decided_by, ...(input.action ? { action: input.action } : {}) }
      let res: Response
      try {
        res = await fetchFn(`${base}/proposals/${encodeURIComponent(proposalId)}/decision`, {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify(body),
        })
      } catch (e) {
        throw new DecisionError('network', e instanceof Error ? e.message : 'Network error')
      }
      if (res.ok) return (await res.json()) as Proposal
      const err = await res.json().catch(() => ({}))
      throw new DecisionError(DECISION_ERRORS[res.status] ?? 'network', err.message ?? `HTTP ${res.status}`, {
        ...(err.current_status ? { current_status: err.current_status } : {}),
        ...('decided_by' in err ? { decided_by: err.decided_by } : {}),
      })
    },

    // No rain or Run endpoints yet (design.md, issues for other lanes).
    rain: async (runId) => (runId === FIXTURE_RUN ? structuredClone(MICHAUNG_RAIN) : []),
    replay: createLocalReplay(),
    commander: unconfigured,
  }
}
