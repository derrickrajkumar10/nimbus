import type { Proposal, WorkOrder } from '@contracts/generated/ts/nimbus'
import {
  confirmationLine,
  deciderName,
  isWorkOrder,
  proposalTitle,
  splitProposals,
  workOrderFacts,
  type ProposalContext,
} from './proposals'
import { proposals, readings, resources, segments } from '../test/fixtures'

const ctx: ProposalContext = { resources, segments, readings, wardName: 'Velachery' }
const workOrder = proposals[0]
const wardAlert: Proposal = {
  ...workOrder,
  proposal_id: 'pr-0002',
  proposed_by: 'herald',
  rank: 2,
  action: { kind: 'ward_alert', message_en: 'Avoid the main road.', message_ta: 'தவிர்க்கவும்.', recipient_count: 1240 },
}
const officer = { officerId: 'officer-1', officerName: 'K. Priya' }

test('proposalTitle for the fixture Work Order', () => {
  expect(proposalTitle(workOrder, ctx)).toBe('Send Pump 2 to Velachery Main Road')
})

test('proposalTitle for a Ward Alert', () => {
  expect(proposalTitle(wardAlert, ctx)).toBe('Ward Alert to everyone in Velachery')
})

test('isWorkOrder tells the actions apart', () => {
  expect(isWorkOrder(workOrder.action)).toBe(true)
  expect(isWorkOrder(wardAlert.action)).toBe(false)
})

test('workOrderFacts', () => {
  const wo = workOrder.action as WorkOrder
  expect(workOrderFacts(wo, readings)).toEqual({ buildings: 17, depth: 'knee', reports: 3 })
  expect(workOrderFacts(wo, [])).toEqual({ buildings: 17, depth: null, reports: 0 })
})

test('splitProposals orders pending by rank and decided by decided_at desc', () => {
  const a = { ...workOrder, proposal_id: 'a', rank: 3 }
  const b = { ...workOrder, proposal_id: 'b', rank: 1 }
  const c = { ...workOrder, proposal_id: 'c', status: 'approved' as const, decided_at: '2023-12-04T02:01:00+05:30' }
  const d = { ...workOrder, proposal_id: 'd', status: 'rejected' as const, decided_at: '2023-12-04T02:05:00+05:30' }
  const { pending, decided } = splitProposals([a, c, b, d])
  expect(pending.map((p) => p.proposal_id)).toEqual(['b', 'a'])
  expect(decided.map((p) => p.proposal_id)).toEqual(['d', 'c'])
})

test('deciderName', () => {
  expect(deciderName('officer-1', 'officer-1', 'K. Priya')).toBe('K. Priya')
  expect(deciderName('officer-2', 'officer-1', 'K. Priya')).toBe('officer-2')
  expect(deciderName(null, 'officer-1', 'K. Priya')).toBe('another officer')
})

test('confirmationLine covers every status for both kinds', () => {
  const c = { ...ctx, ...officer }
  const decided = (p: Proposal, status: 'approved' | 'edited' | 'rejected') => ({ ...p, status, decided_by: 'officer-1' })
  expect(confirmationLine(decided(workOrder, 'approved'), c)).toBe('Approved by K. Priya · Pump 2 en route')
  expect(confirmationLine(decided(workOrder, 'edited'), c)).toBe('Edited and approved by K. Priya · Pump 2 en route')
  expect(confirmationLine(decided(workOrder, 'rejected'), c)).toBe('Rejected by K. Priya')
  expect(confirmationLine(decided(wardAlert, 'approved'), c)).toBe('Approved by K. Priya · Ward Alert sending')
  expect(confirmationLine(decided(wardAlert, 'edited'), c)).toBe('Edited and approved by K. Priya · Ward Alert sending')
  expect(confirmationLine(decided(wardAlert, 'rejected'), c)).toBe('Rejected by K. Priya')
})
