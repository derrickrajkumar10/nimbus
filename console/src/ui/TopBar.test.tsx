import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { fakeSource } from '../test/fakeSource'
import { providers, testConfig } from '../test/render'
import { TopBar } from './TopBar'

test('TopBar shows the fixture clock and Run', async () => {
  render(<TopBar />, { wrapper: providers() })
  expect(await screen.findByText('02:00')).toBeInTheDocument()
  expect(screen.getByText('Mon 4 Dec 2023')).toBeInTheDocument()
  expect(screen.getByText('Replay')).toBeInTheDocument()
  expect(screen.getByText('Cyclone Michaung')).toBeInTheDocument()
  expect(screen.getByText('Velachery ward')).toBeInTheDocument()
  expect(screen.getByText('K. Priya')).toBeInTheDocument()
})

test('TopBar shows a dash for an empty Run', async () => {
  render(<TopBar />, { wrapper: providers(fakeSource(), testConfig({ runId: 'live' })) })
  expect(await screen.findByText('Live')).toBeInTheDocument()
  expect(screen.getByLabelText('Storm time')).toHaveTextContent('—')
})

test('TopBar shows how fresh the data is', async () => {
  render(<TopBar />, { wrapper: providers() })
  expect(await screen.findByText(/Updated \d+ s ago/)).toBeInTheDocument()
})

test('RunSwitcher lists source runs', async () => {
  render(<TopBar />, { wrapper: providers() })
  await userEvent.click(screen.getByRole('button', { name: /Run/ }))
  expect(screen.getByRole('option', { name: /Cyclone Michaung/ })).toBeInTheDocument()
})
