import { readConfig } from './config'

test('readConfig defaults', () => {
  expect(readConfig({}, '')).toEqual({
    apiUrl: null,
    citizenApiUrl: null,
    officerId: 'officer-1',
    officerName: 'K. Priya',
    wardName: 'Velachery',
    runs: ['replay-michaung', 'live'],
    runId: 'replay-michaung',
  })
})

test('readConfig reads ?run= and trims URLs', () => {
  const cfg = readConfig({ VITE_NIMBUS_API: 'https://x/', VITE_CITIZEN_API: 'https://c//', VITE_RUNS: 'live, replay-a' }, '?run=live')
  expect(cfg.apiUrl).toBe('https://x')
  expect(cfg.citizenApiUrl).toBe('https://c')
  expect(cfg.runs).toEqual(['live', 'replay-a'])
  expect(cfg.runId).toBe('live')
})

test('readConfig treats empty strings as unset', () => {
  expect(readConfig({ VITE_NIMBUS_API: '', VITE_OFFICER_NAME: '' }, '?run=')).toMatchObject({
    apiUrl: null,
    officerName: 'K. Priya',
    runId: 'replay-michaung',
  })
})
