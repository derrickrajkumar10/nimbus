import type {
  Event,
  Hazard,
  Proposal,
  Reading,
  Resource1 as Resource,
  Segment,
  SegmentRisk,
} from '@contracts/generated/ts/nimbus'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  useSyncExternalStore,
} from 'react'
import type { Config } from '../config'
import { stormClock } from '../domain/time'
import { DecisionError, type DecisionInput, type NimbusSource, type RainPoint, type SosRow } from './source'

const HEARTBEAT_MS = 2000
const SLOW_MS = 10000

type Heartbeat = { proposals: Proposal[]; risk: SegmentRisk[]; resources: Resource[]; sos: SosRow[]; events: Event[] }

export type ConsoleData = {
  segments: Segment[]
  risk: SegmentRisk[]
  readings: Reading[]
  hazards: Hazard[]
  resources: Resource[]
  sos: SosRow[]
  proposals: Proposal[]
  events: Event[]
  rain: RainPoint[]
  clock: string | null
  isLoading: boolean
}

/** Consecutive heartbeat failures and the wall-clock time of the last success. */
type SyncSnapshot = { failures: number; lastSuccessAt: number | null }

export function createSyncStore() {
  let snap: SyncSnapshot = { failures: 0, lastSuccessAt: null }
  const listeners = new Set<() => void>()
  const set = (next: SyncSnapshot) => {
    snap = next
    listeners.forEach((l) => l())
  }
  return {
    get: () => snap,
    subscribe: (l: () => void) => {
      listeners.add(l)
      return () => listeners.delete(l)
    },
    success: () => set({ failures: 0, lastSuccessAt: Date.now() }),
    failure: () => set({ ...snap, failures: snap.failures + 1 }),
  }
}

type ActivityLog = { cursor: string | null; events: Event[]; seen: Set<string> }

export type SourceCtx = {
  source: NimbusSource
  config: Config
  sync: ReturnType<typeof createSyncStore>
  activity: Map<string, ActivityLog>
}

export const SourceContext = createContext<SourceCtx | null>(null)

function useCtx(): SourceCtx {
  const ctx = useContext(SourceContext)
  if (!ctx) throw new Error('SourceProvider is missing')
  return ctx
}

export function useSource(): NimbusSource {
  return useCtx().source
}

export function useConfig(): Config {
  return useCtx().config
}

const heartbeatKey = (runId: string) => ['heartbeat', runId] as const

export function useConsoleData(): ConsoleData {
  const { source, config, sync, activity } = useCtx()
  const runId = config.runId

  const heartbeat = useQuery({
    queryKey: heartbeatKey(runId),
    queryFn: async (): Promise<Heartbeat> => {
      try {
        let log = activity.get(runId)
        if (!log) activity.set(runId, (log = { cursor: null, events: [], seen: new Set() }))
        const [proposals, risk, resources, sos, page] = await Promise.all([
          source.proposals(runId),
          source.risk(runId),
          source.resources(runId),
          source.sos(runId),
          source.activity(runId, log.cursor),
        ])
        for (const e of page.items) {
          if (!log.seen.has(e.event_id)) {
            log.seen.add(e.event_id)
            log.events.push(e)
          }
        }
        log.cursor = page.cursor ?? log.cursor
        sync.success()
        return { proposals, risk, resources, sos, events: [...log.events] }
      } catch (e) {
        sync.failure()
        throw e
      }
    },
    refetchInterval: HEARTBEAT_MS,
    refetchIntervalInBackground: true,
  })

  const hazards = useQuery({ queryKey: ['hazards', runId], queryFn: () => source.hazards(runId), refetchInterval: SLOW_MS })
  const readings = useQuery({ queryKey: ['readings', runId], queryFn: () => source.readings(runId), refetchInterval: SLOW_MS })
  const segments = useQuery({ queryKey: ['segments'], queryFn: () => source.segments(), staleTime: Infinity })
  const rain = useQuery({ queryKey: ['rain', runId], queryFn: () => source.rain(runId), staleTime: Infinity })

  const hb = heartbeat.data
  const risk = hb?.risk ?? []
  const events = hb?.events ?? []
  return {
    segments: segments.data ?? [],
    risk,
    readings: readings.data ?? [],
    hazards: hazards.data ?? [],
    resources: hb?.resources ?? [],
    sos: hb?.sos ?? [],
    proposals: hb?.proposals ?? [],
    events,
    rain: rain.data ?? [],
    clock: stormClock([...risk.map((r) => r.sim_time), ...events.map((e) => e.sim_time)]),
    isLoading: heartbeat.isPending || segments.isPending,
  }
}

export function useDecide(): (proposalId: string, input: DecisionInput) => Promise<Proposal> {
  const { source, config } = useCtx()
  const qc = useQueryClient()
  const runId = config.runId

  return useCallback(
    async (proposalId, input) => {
      const key = heartbeatKey(runId)
      const patch = (fields: Partial<Proposal>) =>
        qc.setQueryData<Heartbeat>(key, (hb) =>
          hb && {
            ...hb,
            proposals: hb.proposals.map((p) => (p.proposal_id === proposalId ? { ...p, ...fields } : p)),
          },
        )
      await qc.cancelQueries({ queryKey: key })
      const previous = qc.getQueryData<Heartbeat>(key)
      patch({ status: input.decision, decided_by: input.decided_by, ...(input.action ? { action: input.action } : {}) })

      try {
        let decided: Proposal
        try {
          decided = await source.decide(runId, proposalId, input)
        } catch (e) {
          if (!(e instanceof DecisionError && e.code === 'event_not_sent')) throw e
          // The decision was saved; re-sending repeats the same event (api/README.md).
          decided = await source.decide(runId, proposalId, input)
        }
        patch(decided)
        void qc.invalidateQueries({ queryKey: key })
        return decided
      } catch (e) {
        if (e instanceof DecisionError && e.code === 'already_decided') {
          patch({ status: e.detail.current_status, decided_by: e.detail.decided_by ?? null })
        } else {
          qc.setQueryData(key, previous)
        }
        throw e
      }
    },
    [qc, runId, source],
  )
}

export function useSyncStatus(): { secondsAgo: number | null; reconnecting: boolean } {
  const { sync } = useCtx()
  const snap = useSyncExternalStore(sync.subscribe, sync.get)
  // Wall clock for "Updated N s ago" only; it measures the poll, not the storm.
  // A success newer than `now` reads as 0 s until the next tick.
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])
  return {
    secondsAgo: snap.lastSuccessAt === null ? null : Math.max(0, Math.floor((now - snap.lastSuccessAt) / 1000)),
    reconnecting: snap.failures >= 2,
  }
}
