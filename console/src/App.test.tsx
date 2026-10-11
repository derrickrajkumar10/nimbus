import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'
import { fakeSource } from './test/fakeSource'
import { SelectionProbe, providers, testConfig } from './test/render'

vi.mock('maplibre-gl', async () => (await import('./test/maplibre')).maplibreMock())

test('renders the whole fixture scene', async () => {
  render(<App />, { wrapper: providers() })
  expect(await screen.findByRole('article', { name: 'Send Pump 2 to Velachery Main Road' })).toBeInTheDocument()
  for (const region of ['Decisions', 'Map', 'Activity']) {
    expect(screen.getByRole(region === 'Map' ? 'main' : 'complementary', { name: region })).toBeInTheDocument()
  }
  expect(screen.getByText(/Elderly resident/)).toBeInTheDocument()
  expect(screen.getByText('2 of 3 free')).toBeInTheDocument()
  expect(screen.getByText(/Stopped the Herald's ward-wide alert/)).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Play Replay' })).toBeInTheDocument()
  expect(screen.getByLabelText('Ask the Commander')).toBeInTheDocument()
  expect(screen.getByLabelText('Storm time')).toHaveTextContent('02:00')
})

test('empty Run renders empty states without errors', async () => {
  const errors = vi.spyOn(console, 'error')
  render(<App />, { wrapper: providers(fakeSource(), testConfig({ runId: 'live' })) })
  expect(await screen.findByText('Nothing needs you right now.')).toBeInTheDocument()
  expect(screen.getByText('No open SOS.')).toBeInTheDocument()
  expect(screen.getByText('No activity in this Run yet.')).toBeInTheDocument()
  expect(screen.getByLabelText('Storm time')).toHaveTextContent('—')
  expect(screen.queryByRole('button', { name: 'Play Replay' })).toBeNull()
  expect(errors).not.toHaveBeenCalled()
  errors.mockRestore()
})

test('approve flows end to end', async () => {
  render(
    <>
      <App />
      <SelectionProbe />
    </>,
    { wrapper: providers() },
  )
  await screen.findByRole('article', { name: 'Send Pump 2 to Velachery Main Road' })
  await waitFor(() => expect(screen.getByTestId('probe')).toHaveAttribute('data-proposal', 'pr-0001'))
  await userEvent.keyboard('a')
  expect(await screen.findByText('Approved by K. Priya · Pump 2 en route')).toBeInTheDocument()
  expect(await screen.findByText('Approved the Work Order: Send Pump 2 to Velachery Main Road.')).toBeInTheDocument()
})
