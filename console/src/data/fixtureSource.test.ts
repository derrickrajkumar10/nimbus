import { createFixtureSource } from './fixtureSource'
import { DecisionError } from './source'

const RUN = 'replay-michaung'
const approve = { decision: 'approved' as const, decided_by: 'officer-1' }

async function codeOf(p: Promise<unknown>): Promise<string> {
  try {
    await p
  } catch (e) {
    return e instanceof DecisionError ? e.code : 'not a DecisionError'
  }
  return 'resolved'
}

test('serves the fixture scene for replay-michaung', async () => {
  const s = createFixtureSource()
  expect(s.mode).toBe('fixtures')
  expect(s.runs()).toEqual([RUN])
  expect(await s.risk(RUN)).toHaveLength(21)
  expect(await s.resources(RUN)).toHaveLength(3)
  expect(await s.sos(RUN)).toHaveLength(1)
  expect(await s.proposals(RUN)).toHaveLength(2)
  expect(await s.hazards(RUN)).toHaveLength(1)
  expect(await s.readings(RUN)).toHaveLength(1)
  expect(await s.segments()).toHaveLength(21)
  expect(await s.rain(RUN)).toHaveLength(19)
})

test('serves nothing for another Run', async () => {
  const s = createFixtureSource()
  const calls: ((run: string) => Promise<unknown[]>)[] = [
    s.risk, s.readings, s.hazards, s.resources, s.sos, s.proposals, s.rain,
  ]
  for (const call of calls) expect(await call('live')).toEqual([])
  expect(await s.activity('live')).toEqual({ items: [], cursor: null })
})

test('pages activity with an exclusive cursor', async () => {
  const s = createFixtureSource()
  const first = await s.activity(RUN)
  expect(first.items).toHaveLength(8)
  expect(first.items[0].sim_time).toBe('2023-12-04T01:45:00+05:30')
  const next = await s.activity(RUN, first.cursor)
  expect(next.items).toHaveLength(0)
})

test('approves a pending Proposal', async () => {
  const s = createFixtureSource()
  const p = await s.decide(RUN, 'pr-0001', approve)
  expect(p).toMatchObject({ status: 'approved', decided_by: 'officer-1' })
  expect((await s.proposals(RUN)).find((x) => x.proposal_id === 'pr-0001')?.status).toBe('approved')
})

test('repeat of the same decision by the same officer is idempotent', async () => {
  const s = createFixtureSource()
  await s.decide(RUN, 'pr-0001', approve)
  expect((await s.decide(RUN, 'pr-0001', approve)).status).toBe('approved')
})

test('rejects a different decision with already_decided', async () => {
  const s = createFixtureSource()
  await s.decide(RUN, 'pr-0001', approve)
  const err = await s.decide(RUN, 'pr-0001', { decision: 'rejected', decided_by: 'officer-1' }).catch((e) => e)
  expect(err).toBeInstanceOf(DecisionError)
  expect(err.code).toBe('already_decided')
  expect(err.detail).toEqual({ current_status: 'approved', decided_by: 'officer-1' })
})

test('pre-decided Proposals report the other officer', async () => {
  const s = createFixtureSource({ decidedBy: { 'pr-0001': 'officer-2' } })
  const err = await s.decide(RUN, 'pr-0001', approve).catch((e) => e)
  expect(err.code).toBe('already_decided')
  expect(err.detail.decided_by).toBe('officer-2')
})

test('validates edited actions', async () => {
  const s = createFixtureSource()
  expect(await codeOf(s.decide(RUN, 'pr-0002', { decision: 'edited', decided_by: 'officer-1' }))).toBe('invalid')
  const action = { kind: 'ward_alert' as const, message_en: 'x', message_ta: 'y', recipient_count: 1 }
  expect(await codeOf(s.decide(RUN, 'pr-0002', { ...approve, action }))).toBe('invalid')
  const edited = await s.decide(RUN, 'pr-0002', { decision: 'edited', decided_by: 'officer-1', action })
  expect(edited).toMatchObject({ status: 'edited', action: { message_en: 'x' } })
})

test('unknown proposal', async () => {
  expect(await codeOf(createFixtureSource().decide(RUN, 'nope', approve))).toBe('proposal_not_found')
})

test('local replay control remembers play state and speed', async () => {
  const s = createFixtureSource()
  expect(s.replay.get(RUN)).toEqual({ playing: false, speed: 60 })
  expect(await s.replay.set(RUN, { playing: true, speed: 120 })).toEqual({ playing: true, speed: 120 })
  expect(s.replay.get(RUN)).toEqual({ playing: true, speed: 120 })
})
