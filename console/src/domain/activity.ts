import type { Agent, Event, Proposal } from '@contracts/generated/ts/nimbus'
import { deciderName, isWorkOrder, proposalTitle, type ProposalContext } from './proposals'

export type FeedItem =
  | { kind: 'agent'; id: string; time: string; agent: Agent; decided: string; saw: string; why: string }
  | { kind: 'cedar'; id: string; time: string; principal: Agent; action: string; reason: string }
  | { kind: 'officer'; id: string; time: string; who: string; text: string }
  | { kind: 'commander'; id: string; time: string | null; question: string; answer: string; streaming: boolean }

export type FeedFilter = 'all' | 'cedar' | Agent

export const AGENT_LABEL: Record<Agent, string> = {
  sentinel: 'Sentinel',
  verifier: 'Verifier',
  triage: 'Triage',
  pathfinder: 'Pathfinder',
  dispatcher: 'Dispatcher',
  herald: 'Herald',
  chronicler: 'Chronicler',
  commander: 'Commander',
}

function officerText(p: Proposal, title: string): string {
  if (p.status === 'rejected') return `Rejected: ${title}.`
  const verb = p.status === 'edited' ? 'Edited and approved' : 'Approved'
  return isWorkOrder(p.action) ? `${verb} the Work Order: ${title}.` : `${verb} the Ward Alert.`
}

/**
 * The feed, newest first. Allowed Cedar decisions are noise and dropped.
 * At equal times, later events and officer decisions come first.
 */
export function toFeedItems(
  events: Event[],
  decided: Proposal[],
  ctx: ProposalContext & { officerId: string; officerName: string },
): FeedItem[] {
  const keyed: { ms: number; seq: number; item: FeedItem }[] = []
  events.forEach((e, seq) => {
    const ms = Date.parse(e.sim_time)
    if (e.type === 'agent.activity') {
      const d = e.detail
      keyed.push({ ms, seq, item: { kind: 'agent', id: e.event_id, time: e.sim_time, agent: d.agent, decided: d.decided, saw: d.saw, why: d.why } })
    } else if (e.type === 'policy.decided' && !e.detail.allowed) {
      const d = e.detail
      keyed.push({ ms, seq, item: { kind: 'cedar', id: e.event_id, time: e.sim_time, principal: d.principal, action: d.action, reason: d.reason } })
    }
  })
  decided.forEach((p, i) => {
    const time = p.decided_at ?? p.created_at
    keyed.push({
      ms: Date.parse(time),
      seq: events.length + i,
      item: {
        kind: 'officer',
        id: `officer-${p.proposal_id}`,
        time,
        who: deciderName(p.decided_by, ctx.officerId, ctx.officerName),
        text: officerText(p, proposalTitle(p, ctx)),
      },
    })
  })
  return keyed.sort((a, b) => b.ms - a.ms || b.seq - a.seq).map((k) => k.item)
}

export function filterFeed(items: FeedItem[], f: FeedFilter): FeedItem[] {
  if (f === 'all') return items
  return items.filter(
    (i) => i.kind === 'commander' || (f === 'cedar' ? i.kind === 'cedar' : i.kind === 'agent' && i.agent === f),
  )
}
