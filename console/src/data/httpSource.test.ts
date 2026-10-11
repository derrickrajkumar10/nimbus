import { readConfig } from '../config'
import { createSource } from './createSource'
import { createHttpSource } from './httpSource'
import { DecisionError } from './source'

const RUN = 'replay-michaung'
const cfg = readConfig({ VITE_NIMBUS_API: 'https://x' }, '')

function mockFetch(respond: (url: string, init?: RequestInit) => Response | Promise<Response>) {
  const calls: { url: string; init?: RequestInit }[] = []
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    calls.push({ url, init })
    return respond(url, init)
  }) as unknown as typeof fetch
  return { fn, calls }
}

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } })

test('createSource picks fixtures without an API URL and http with one', () => {
  expect(createSource(readConfig({}, '')).mode).toBe('fixtures')
  expect(createSource(cfg).mode).toBe('http')
})

test('http GETs carry run_id', async () => {
  const { fn, calls } = mockFetch(() => json([]))
  const s = createHttpSource(cfg, fn)
  await s.risk(RUN)
  await s.proposals(RUN)
  expect(calls.map((c) => c.url)).toEqual([
    'https://x/risk?run_id=replay-michaung',
    'https://x/proposals?run_id=replay-michaung',
  ])
})

test('http activity omits since on first call and passes cursor after', async () => {
  const { fn, calls } = mockFetch(() => json({ items: [], cursor: 'c1' }))
  const s = createHttpSource(cfg, fn)
  const page = await s.activity(RUN)
  await s.activity(RUN, page.cursor)
  expect(calls[0].url).toBe('https://x/activity?run_id=replay-michaung&limit=500')
  expect(calls[1].url).toBe('https://x/activity?run_id=replay-michaung&limit=500&since=c1')
})

test('http decide posts the documented body', async () => {
  const { fn, calls } = mockFetch(() => json({ proposal_id: 'pr-0001', status: 'approved' }))
  await createHttpSource(cfg, fn).decide(RUN, 'pr-0001', { decision: 'approved', decided_by: 'officer-1' })
  expect(calls[0].url).toBe('https://x/proposals/pr-0001/decision')
  expect(calls[0].init?.method).toBe('POST')
  expect(JSON.parse(String(calls[0].init?.body))).toEqual({
    run_id: 'replay-michaung',
    decision: 'approved',
    decided_by: 'officer-1',
  })
})

test('http decide maps 409 with detail', async () => {
  const { fn } = mockFetch(() =>
    json({ error: 'already_decided', message: 'x', current_status: 'approved', decided_by: 'officer-2' }, 409),
  )
  const err = await createHttpSource(cfg, fn)
    .decide(RUN, 'pr-0001', { decision: 'approved', decided_by: 'officer-1' })
    .catch((e) => e)
  expect(err).toBeInstanceOf(DecisionError)
  expect(err.code).toBe('already_decided')
  expect(err.detail).toEqual({ current_status: 'approved', decided_by: 'officer-2' })
})

test('http decide maps 404, 422 and 502', async () => {
  for (const [status, code] of [[404, 'proposal_not_found'], [422, 'invalid'], [502, 'event_not_sent']] as const) {
    const { fn } = mockFetch(() => json({ error: 'x', message: 'x' }, status))
    const err = await createHttpSource(cfg, fn)
      .decide(RUN, 'pr-0001', { decision: 'approved', decided_by: 'officer-1' })
      .catch((e) => e)
    expect(err.code).toBe(code)
  }
})

test('http decide maps a fetch rejection to network', async () => {
  const fn = vi.fn(() => Promise.reject(new TypeError('offline'))) as unknown as typeof fetch
  const err = await createHttpSource(cfg, fn)
    .decide(RUN, 'pr-0001', { decision: 'approved', decided_by: 'officer-1' })
    .catch((e) => e)
  expect(err.code).toBe('network')
})

test('a failed GET throws with its status', async () => {
  const { fn } = mockFetch(() => json({ error: 'x' }, 500))
  await expect(createHttpSource(cfg, fn).risk(RUN)).rejects.toThrow('500')
})

test('segments come from the citizen API when configured', async () => {
  const { fn, calls } = mockFetch(() => json([]))
  await createHttpSource(readConfig({ VITE_NIMBUS_API: 'https://x', VITE_CITIZEN_API: 'https://c' }, ''), fn).segments()
  expect(calls[0].url).toBe('https://c/segments')
})

test('segments fall back to the fixture without a citizen API', async () => {
  const { fn, calls } = mockFetch(() => json([]))
  expect(await createHttpSource(cfg, fn).segments()).toHaveLength(21)
  expect(calls).toHaveLength(0)
})
