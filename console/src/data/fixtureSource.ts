import hazardsJson from '@contracts/fixtures/hazards.json'
import proposalsJson from '@contracts/fixtures/proposals.json'
import readingsJson from '@contracts/fixtures/readings.json'
import resourcesJson from '@contracts/fixtures/resources.json'
import riskJson from '@contracts/fixtures/risk.json'
import segmentsJson from '@contracts/fixtures/segments.json'
import sosJson from '@contracts/fixtures/sos.json'
import type {
  Hazard,
  Proposal,
  Reading,
  Resource1 as Resource,
  Segment,
  SegmentRisk,
} from '@contracts/generated/ts/nimbus'
import { MICHAUNG_RAIN, SCENE_EVENTS, SCENE_WARD_ALERT } from './fixtureScene'
import {
  DecisionError,
  type CommanderClient,
  type DecisionInput,
  type NimbusSource,
  type ReplayControl,
  type ReplayState,
  type SosRow,
} from './source'

export const FIXTURE_RUN = 'replay-michaung'
export const FIXTURE_SEGMENTS = segmentsJson as unknown as Segment[]

/** Replay controls kept in memory until `POST /runs` exists. */
export function createLocalReplay(): ReplayControl {
  const states = new Map<string, ReplayState>()
  return {
    get: (runId) => states.get(runId) ?? { playing: false, speed: 60 },
    set: async (runId, next) => {
      states.set(runId, next)
      return next
    },
  }
}

const unconfigured: CommanderClient = {
  ask() {
    throw new Error('commander not configured')
  },
}

const clone = <T>(v: T): T => structuredClone(v)

export function createFixtureSource(opts: { decidedBy?: Record<string, string> } = {}): NimbusSource {
  const proposals = new Map<string, Proposal>()
  for (const p of [...(proposalsJson as unknown as Proposal[]), SCENE_WARD_ALERT]) {
    const by = opts.decidedBy?.[p.proposal_id]
    proposals.set(
      p.proposal_id,
      by ? { ...clone(p), status: 'approved', decided_by: by, decided_at: p.created_at } : clone(p),
    )
  }

  const forRun = <T>(runId: string, rows: unknown): Promise<T[]> =>
    Promise.resolve(runId === FIXTURE_RUN ? clone(rows as T[]) : [])

  return {
    mode: 'fixtures',
    runs: () => [FIXTURE_RUN],
    segments: () => Promise.resolve(clone(FIXTURE_SEGMENTS)),
    risk: (runId) => forRun<SegmentRisk>(runId, riskJson),
    readings: (runId) => forRun<Reading>(runId, readingsJson),
    hazards: (runId) => forRun<Hazard>(runId, hazardsJson),
    resources: (runId) => forRun<Resource>(runId, resourcesJson),
    sos: (runId) => forRun<SosRow>(runId, sosJson),
    proposals: (runId) => forRun<Proposal>(runId, [...proposals.values()]),
    rain: (runId) => forRun(runId, MICHAUNG_RAIN),

    async activity(runId, since) {
      if (runId !== FIXTURE_RUN) return { items: [], cursor: null }
      const from = since ? Number(since) : 0
      const items = clone(SCENE_EVENTS.slice(from))
      return { items, cursor: String(SCENE_EVENTS.length) }
    },

    async decide(runId, proposalId, input: DecisionInput) {
      const p = runId === FIXTURE_RUN ? proposals.get(proposalId) : undefined
      if (!p) throw new DecisionError('proposal_not_found', `No Proposal ${proposalId} in ${runId}`)
      if ((input.decision === 'edited') !== Boolean(input.action)) {
        throw new DecisionError('invalid', 'An edited decision needs an action; others must not carry one')
      }
      const status = p.status ?? 'pending'
      if (status !== 'pending') {
        if (status === input.decision && p.decided_by === input.decided_by) return clone(p)
        throw new DecisionError('already_decided', `Already ${status}`, {
          current_status: status,
          decided_by: p.decided_by,
        })
      }
      const decided: Proposal = {
        ...p,
        status: input.decision,
        decided_by: input.decided_by,
        decided_at: p.created_at,
        action: input.action ?? p.action,
      }
      proposals.set(proposalId, decided)
      return clone(decided)
    },

    replay: createLocalReplay(),
    commander: unconfigured,
  }
}
