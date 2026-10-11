import type { Proposal } from '@contracts/generated/ts/nimbus'
import { SCENE_EVENTS } from '../data/fixtureScene'
import { proposals, readings, resources, segments } from '../test/fixtures'
import { AGENT_LABEL, filterFeed, toFeedItems, type FeedItem } from './activity'

const ctx = { resources, segments, readings, wardName: 'Velachery', officerId: 'officer-1', officerName: 'K. Priya' }

test('toFeedItems builds the fixture feed', () => {
  const items = toFeedItems(SCENE_EVENTS, [], ctx)
  expect(items).toHaveLength(7)
  expect(items[0]).toMatchObject({
    kind: 'cedar',
    principal: 'herald',
    reason: "Stopped the Herald's ward-wide alert until an officer approves it.",
  })
  expect(items[1]).toMatchObject({ kind: 'agent', agent: 'dispatcher' })
  expect(items[6]).toMatchObject({ kind: 'agent', agent: 'pathfinder' })
})

test('toFeedItems adds officer rows from decided Proposals', () => {
  const decided: Proposal = { ...proposals[0], status: 'approved', decided_by: 'officer-1', decided_at: '2023-12-04T02:00:00+05:30' }
  const items = toFeedItems(SCENE_EVENTS, [decided], ctx)
  expect(items[0]).toMatchObject({
    kind: 'officer',
    who: 'K. Priya',
    text: 'Approved the Work Order: Send Pump 2 to Velachery Main Road.',
  })
})

test('officer rows word every decision', () => {
  const at = '2023-12-04T02:01:00+05:30'
  const wa: Proposal = {
    ...proposals[0],
    proposal_id: 'pr-0002',
    action: { kind: 'ward_alert', message_en: 'x', message_ta: 'y', recipient_count: 1 },
  }
  const text = (p: Proposal, status: 'approved' | 'edited' | 'rejected', by = 'officer-1') =>
    (toFeedItems([], [{ ...p, status, decided_by: by, decided_at: at }], ctx)[0] as Extract<FeedItem, { kind: 'officer' }>)
  expect(text(wa, 'approved').text).toBe('Approved the Ward Alert.')
  expect(text(wa, 'edited').text).toBe('Edited and approved the Ward Alert.')
  expect(text(proposals[0], 'edited').text).toBe('Edited and approved the Work Order: Send Pump 2 to Velachery Main Road.')
  expect(text(proposals[0], 'rejected').text).toBe('Rejected: Send Pump 2 to Velachery Main Road.')
  expect(text(proposals[0], 'approved', 'officer-2').who).toBe('officer-2')
})

test('filterFeed narrows to Cedar and to one agent', () => {
  const commander: FeedItem = { kind: 'commander', id: 'q1', time: null, question: 'q', answer: 'a', streaming: false }
  const items = [commander, ...toFeedItems(SCENE_EVENTS, [], ctx)]
  expect(filterFeed(items, 'all')).toHaveLength(8)
  expect(filterFeed(items, 'cedar').map((i) => i.kind)).toEqual(['commander', 'cedar'])
  const verifier = filterFeed(items, 'verifier')
  expect(verifier).toHaveLength(3)
  expect(verifier.slice(1).every((i) => i.kind === 'agent' && i.agent === 'verifier')).toBe(true)
})

test('agent labels', () => {
  expect(AGENT_LABEL.sentinel).toBe('Sentinel')
  expect(AGENT_LABEL.commander).toBe('Commander')
})
