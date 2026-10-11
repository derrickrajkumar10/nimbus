import type {
  DepthBand,
  Proposal,
  Reading,
  Resource1 as Resource,
  Segment,
  WorkOrder,
} from '@contracts/generated/ts/nimbus'
import { streetName } from './geo'

export type ProposalContext = { resources: Resource[]; segments: Segment[]; readings: Reading[]; wardName: string }

const DEPTH_ORDER: DepthBand[] = ['dry', 'ankle', 'knee', 'waist', 'above_waist']

export function isWorkOrder(a: Proposal['action']): a is WorkOrder {
  return a.kind === 'work_order' || 'resource_id' in a
}

function resourceLabel(id: string, ctx: Pick<ProposalContext, 'resources'>): string {
  return ctx.resources.find((r) => r.resource_id === id)?.label ?? id
}

export function proposalTitle(p: Proposal, ctx: ProposalContext): string {
  if (!isWorkOrder(p.action)) return `Ward Alert to everyone in ${ctx.wardName}`
  const { resource_id, segment_id } = p.action
  const segment = ctx.segments.find((s) => s.segment_id === segment_id)
  return `Send ${resourceLabel(resource_id, ctx)} to ${segment ? streetName(segment) : segment_id}`
}

export function workOrderFacts(
  wo: WorkOrder,
  readings: Reading[],
): { buildings: number; depth: DepthBand | null; reports: number } {
  const linked = readings.filter((r) => wo.reading_ids?.includes(r.reading_id))
  let depth: DepthBand | null = null
  for (const r of linked) {
    if (depth === null || DEPTH_ORDER.indexOf(r.depth) > DEPTH_ORDER.indexOf(depth)) depth = r.depth
  }
  return {
    buildings: wo.buildings_affected,
    depth,
    reports: linked.reduce((n, r) => n + r.report_ids.length, 0),
  }
}

export function splitProposals(ps: Proposal[]): { pending: Proposal[]; decided: Proposal[] } {
  const pending = ps.filter((p) => (p.status ?? 'pending') === 'pending').sort((a, b) => a.rank - b.rank)
  const decided = ps
    .filter((p) => (p.status ?? 'pending') !== 'pending')
    .sort((a, b) => Date.parse(b.decided_at ?? b.created_at) - Date.parse(a.decided_at ?? a.created_at))
  return { pending, decided }
}

export function deciderName(decidedBy: string | null | undefined, officerId: string, officerName: string): string {
  if (!decidedBy) return 'another officer'
  return decidedBy === officerId ? officerName : decidedBy
}

export function confirmationLine(
  p: Proposal,
  ctx: ProposalContext & { officerId: string; officerName: string },
): string {
  const name = deciderName(p.decided_by, ctx.officerId, ctx.officerName)
  if (p.status === 'rejected') return `Rejected by ${name}`
  const verb = p.status === 'edited' ? 'Edited and approved by' : 'Approved by'
  const outcome = isWorkOrder(p.action) ? `${resourceLabel(p.action.resource_id, ctx)} en route` : 'Ward Alert sending'
  return `${verb} ${name} · ${outcome}`
}
