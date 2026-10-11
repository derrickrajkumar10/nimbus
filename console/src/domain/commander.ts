import type {
  Event,
  Proposal,
  Reading,
  Resource1 as Resource,
  Segment,
  SegmentRisk,
} from '@contracts/generated/ts/nimbus'
import type { SosRow } from '../data/source'
import { streetName } from './geo'
import { proposalTitle, splitProposals } from './proposals'

export type Snapshot = {
  risk: SegmentRisk[]
  segments: Segment[]
  proposals: Proposal[]
  events: Event[]
  sos: SosRow[]
  resources: Resource[]
  readings: Reading[]
  clock: string | null
  wardName: string
}

const HOUR_MS = 3600000
const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`

/**
 * The fixture Commander's answer: what changed in the last hour, what's waiting,
 * and the top risk. Grounded only in the snapshot, so it never invents facts.
 */
export function buildCommanderAnswer(_question: string, s: Snapshot): string {
  const { pending } = splitProposals(s.proposals)
  if (!s.events.length && !pending.length && !s.risk.length) return 'Nothing has happened in this Run yet.'

  const street = (id: string) => {
    const seg = s.segments.find((x) => x.segment_id === id)
    return seg ? streetName(seg) : id
  }

  const end = s.clock ? Date.parse(s.clock) : Infinity
  const recent = s.events.filter((e) => {
    const t = Date.parse(e.sim_time)
    const counts = e.type === 'agent.activity' || (e.type === 'policy.decided' && !e.detail.allowed)
    return counts && t <= end && t > end - HOUR_MS
  })
  const latest = recent
    .flatMap((e) => (e.type === 'agent.activity' ? [e.detail.decided] : []))
    .slice(-2)
    .reverse()
  const changed = recent.length
    ? `In the last hour the agents logged ${plural(recent.length, 'agent action')}. Most recent: ${latest.join(' ')}`
    : 'No agent actions in the last hour.'

  const ctx = { resources: s.resources, segments: s.segments, readings: s.readings, wardName: s.wardName }
  const waiting = pending.length
    ? `${plural(pending.length, 'Decision is', 'Decisions are')} waiting for you: ${pending.map((p) => proposalTitle(p, ctx)).join('; ')}.`
    : 'Nothing is waiting for your approval.'

  const flooded = [...new Set(s.risk.filter((r) => r.band === 'flooded').map((r) => street(r.segment_id)))]
  const likely = s.risk.filter((r) => r.band === 'likely').sort((a, b) => b.score - a.score)
  const parts: string[] = []
  if (flooded.length) parts.push(`Flooded now: ${flooded.join(', ')}.`)
  if (likely.length) {
    const top = likely[0]
    const why = top.reasons[0]?.text
    parts.push(
      `${plural(likely.length, 'Segment is', 'Segments are')} likely to flood. Highest: ${street(top.segment_id)}, score ${top.score}${why ? `, ${why.charAt(0).toLowerCase()}${why.slice(1)}` : ''}.`,
    )
  }
  const risk = parts.length ? parts.join(' ') : 'No Segment is flooded or likely to flood.'

  return [changed, waiting, risk].join('\n\n')
}
