import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../App'
import { fakeSource } from '../test/fakeSource'
import { providers, testConfig } from '../test/render'
import { ReplayBar } from './ReplayBar'

vi.mock('maplibre-gl', async () => (await import('../test/maplibre')).maplibreMock())

test('Space toggles play and the label flips', async () => {
  const source = fakeSource()
  render(<ReplayBar />, { wrapper: providers(source) })
  expect(await screen.findByRole('button', { name: 'Play Replay' })).toBeInTheDocument()
  await userEvent.keyboard(' ')
  expect(await screen.findByRole('button', { name: 'Pause Replay' })).toBeInTheDocument()
  expect(source.replay.get('replay-michaung').playing).toBe(true)
})

test('speed button cycles 60× → 120×', async () => {
  render(<ReplayBar />, { wrapper: providers() })
  await userEvent.click(await screen.findByRole('button', { name: /60×/ }))
  expect(await screen.findByRole('button', { name: /120×/ })).toBeInTheDocument()
})

test('the playhead label reads the storm clock and its rain', async () => {
  render(<ReplayBar />, { wrapper: providers() })
  expect(await screen.findByText('02:00 · 3.2 mm/h')).toBeInTheDocument()
  expect(screen.getByText('18:00 · 3 Dec')).toBeInTheDocument()
})

test('App hides the Replay bar on a live Run', async () => {
  render(<App />, { wrapper: providers(fakeSource(), testConfig({ runId: 'live' })) })
  expect(await screen.findByText('Nothing needs you right now.')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /Replay$/ })).toBeNull()
})

test('App shows the Replay bar on a Replay Run', async () => {
  render(<App />, { wrapper: providers() })
  expect(await screen.findByRole('button', { name: 'Play Replay' })).toBeInTheDocument()
})
