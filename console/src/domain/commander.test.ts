import { SCENE_EVENTS, SCENE_WARD_ALERT } from '../data/fixtureScene'
import { createFixtureCommander, registerSnapshot } from '../data/fixtureCommander'
import { proposals, readings, resources, risk, segments, sos } from '../test/fixtures'
import { buildCommanderAnswer, type Snapshot } from './commander'

const snap: Snapshot = {
  risk,
  segments,
  proposals: [...proposals, SCENE_WARD_ALERT],
  events: SCENE_EVENTS,
  sos,
  resources,
  readings,
  clock: '2023-12-04T02:00:00+05:30',
  wardName: 'Velachery',
}

const empty: Snapshot = { ...snap, risk: [], proposals: [], events: [], sos: [], clock: null }

test('answer mentions the pending titles and the flooded street', () => {
  const a = buildCommanderAnswer('What changed in the last hour?', snap)
  expect(a).toContain('Send Pump 2 to Velachery Main Road')
  expect(a).toContain('Ward Alert to everyone in Velachery')
  expect(a).toContain('Flooded now: Velachery Main Road')
  expect(a).toContain('7 agent actions')
  expect(a.split('\n\n')).toHaveLength(3)
})

test('empty snapshot answer', () => {
  expect(buildCommanderAnswer('Anything?', empty)).toBe('Nothing has happened in this Run yet.')
})

test('fixture commander streams the whole answer', async () => {
  registerSnapshot(() => snap)
  const q = 'What changed in the last hour?'
  let joined = ''
  let chunks = 0
  for await (const c of createFixtureCommander({ delayMs: 0 }).ask(q, 'replay-michaung')) {
    joined += c
    chunks++
  }
  expect(joined).toBe(buildCommanderAnswer(q, snap))
  expect(chunks).toBeGreaterThan(10)
})
