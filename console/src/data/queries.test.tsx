import { act, renderHook, waitFor } from '@testing-library/react'
import { fakeSource } from '../test/fakeSource'
import { providers, testConfig } from '../test/render'
import { useConsoleData, useDecide, useSyncStatus } from './queries'
import { DecisionError } from './source'

const approve = { decision: 'approved' as const, decided_by: 'officer-1' }

function useBoth() {
  return { data: useConsoleData(), decide: useDecide(), sync: useSyncStatus() }
}

afterEach(() => vi.useRealTimers())

test('loads the fixture scene', async () => {
  const { result } = renderHook(useConsoleData, { wrapper: providers() })
  await waitFor(() => expect(result.current.isLoading).toBe(false))
  expect(result.current.proposals).toHaveLength(2)
  expect(result.current.events).toHaveLength(8)
  expect(result.current.segments).toHaveLength(21)
  expect(result.current.rain).toHaveLength(19)
  expect(result.current.clock).toBe('2023-12-04T02:00:00+05:30')
})

test('empty Run gives empty data and a null clock', async () => {
  const { result } = renderHook(useConsoleData, { wrapper: providers(fakeSource(), testConfig({ runId: 'live' })) })
  await waitFor(() => expect(result.current.isLoading).toBe(false))
  expect(result.current.proposals).toEqual([])
  expect(result.current.events).toEqual([])
  expect(result.current.clock).toBeNull()
})

test('optimistic approve then confirmed', async () => {
  const { result } = renderHook(useBoth, { wrapper: providers() })
  await waitFor(() => expect(result.current.data.isLoading).toBe(false))
  await act(() => result.current.decide('pr-0001', approve))
  const p = result.current.data.proposals.find((x) => x.proposal_id === 'pr-0001')
  expect(p).toMatchObject({ status: 'approved', decided_by: 'officer-1' })
})

test('already_decided writes the other officer into the cache and throws', async () => {
  const source = fakeSource({
    decide: () =>
      Promise.reject(new DecisionError('already_decided', 'x', { current_status: 'approved', decided_by: 'officer-2' })),
  })
  const { result } = renderHook(useBoth, { wrapper: providers(source) })
  await waitFor(() => expect(result.current.data.isLoading).toBe(false))
  await act(() => expect(result.current.decide('pr-0001', approve)).rejects.toThrow(DecisionError))
  await waitFor(() =>
    expect(result.current.data.proposals.find((x) => x.proposal_id === 'pr-0001')).toMatchObject({
      status: 'approved',
      decided_by: 'officer-2',
    }),
  )
})

test('network error rolls back', async () => {
  const source = fakeSource({ decide: () => Promise.reject(new DecisionError('network', 'offline')) })
  const { result } = renderHook(useBoth, { wrapper: providers(source) })
  await waitFor(() => expect(result.current.data.isLoading).toBe(false))
  await act(() => expect(result.current.decide('pr-0001', approve)).rejects.toThrow('offline'))
  expect(result.current.data.proposals.find((x) => x.proposal_id === 'pr-0001')?.status).toBe('pending')
})

test('event_not_sent retries once', async () => {
  const base = fakeSource()
  const decide = vi
    .fn()
    .mockRejectedValueOnce(new DecisionError('event_not_sent', 'x'))
    .mockImplementation(base.decide)
  const { result } = renderHook(useBoth, { wrapper: providers({ ...base, decide }) })
  await waitFor(() => expect(result.current.data.isLoading).toBe(false))
  await act(() => result.current.decide('pr-0001', approve))
  expect(decide).toHaveBeenCalledTimes(2)
  expect(result.current.data.proposals.find((x) => x.proposal_id === 'pr-0001')?.status).toBe('approved')
})

test('a heartbeat during an in-flight decision keeps the optimistic state', async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  const base = fakeSource()
  let release!: () => void
  const gate = new Promise<void>((r) => (release = r))
  const decide = vi.fn(async (...args: Parameters<typeof base.decide>) => {
    await gate
    return base.decide(...args)
  })
  const { result } = renderHook(useBoth, { wrapper: providers({ ...base, decide }) })
  await waitFor(() => expect(result.current.data.isLoading).toBe(false))
  let done!: Promise<unknown>
  act(() => {
    done = result.current.decide('pr-0001', approve)
  })
  await act(() => vi.advanceTimersByTimeAsync(2100)) // a poll lands; the source still says pending
  expect(result.current.data.proposals.find((x) => x.proposal_id === 'pr-0001')?.status).toBe('approved')
  release()
  await act(() => done)
})

test('a failed decision rolls back only its own Proposal', async () => {
  const base = fakeSource()
  const decide = vi.fn(async (run: string, id: string, input: Parameters<typeof base.decide>[2]) => {
    if (id === 'pr-0001') {
      await new Promise((r) => setTimeout(r, 30))
      throw new DecisionError('network', 'offline')
    }
    return base.decide(run, id, input)
  })
  const { result } = renderHook(useBoth, { wrapper: providers({ ...base, decide }) })
  await waitFor(() => expect(result.current.data.isLoading).toBe(false))
  await act(async () => {
    const first = result.current.decide('pr-0001', approve).catch(() => undefined)
    await result.current.decide('pr-0002', approve)
    await first
  })
  await waitFor(() => {
    const byId = Object.fromEntries(result.current.data.proposals.map((p) => [p.proposal_id, p.status]))
    expect(byId).toEqual({ 'pr-0001': 'pending', 'pr-0002': 'approved' })
  })
})

test('two failed polls mark reconnecting, then recovery clears it', async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  const base = fakeSource()
  const proposals = vi
    .fn()
    .mockRejectedValueOnce(new Error('down'))
    .mockRejectedValueOnce(new Error('down'))
    .mockImplementation(base.proposals)
  const { result } = renderHook(
    () => {
      useConsoleData()
      return useSyncStatus()
    },
    { wrapper: providers({ ...base, proposals }) },
  )
  await waitFor(() => expect(proposals).toHaveBeenCalledTimes(1))
  expect(result.current.reconnecting).toBe(false)
  await act(() => vi.advanceTimersByTimeAsync(2000))
  await waitFor(() => expect(result.current.reconnecting).toBe(true))
  await act(() => vi.advanceTimersByTimeAsync(2000))
  await waitFor(() => expect(result.current.reconnecting).toBe(false))
  expect(result.current.secondsAgo).toBe(0)
})
