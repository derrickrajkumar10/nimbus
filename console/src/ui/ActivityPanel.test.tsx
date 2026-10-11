import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { FeedItem } from '../domain/activity'
import { fakeSource } from '../test/fakeSource'
import { providers } from '../test/render'
import { ActivityPanel } from './ActivityPanel'

test('ActivityPanel shows Held on the Cedar row and expands an agent row', async () => {
  render(<ActivityPanel />, { wrapper: providers() })
  const cedar = await screen.findByText("Stopped the Herald's ward-wide alert until an officer approves it.")
  expect(within(cedar.closest('li')!).getByText('Held')).toBeInTheDocument()
  const verifier = screen.getByRole('button', { name: /Merged 3 Reports/ })
  expect(verifier).toHaveAttribute('aria-expanded', 'false')
  await userEvent.click(verifier)
  expect(verifier).toHaveAttribute('aria-expanded', 'true')
  expect(screen.getByText(/Saw:/)).toBeInTheDocument()
  expect(screen.getByText(/Why:/)).toBeInTheDocument()
})

test('approving in the store adds an officer row', async () => {
  const source = fakeSource({}, { decidedBy: { 'pr-0001': 'officer-1' } })
  render(<ActivityPanel />, { wrapper: providers(source) })
  expect(await screen.findByText('Approved the Work Order: Send Pump 2 to Velachery Main Road.')).toBeInTheDocument()
  expect(screen.getByText('K. Priya')).toBeInTheDocument()
})

test('the filter narrows the feed to one agent', async () => {
  render(<ActivityPanel />, { wrapper: providers() })
  await screen.findByText(/Merged 3 Reports/)
  await userEvent.click(screen.getByRole('button', { name: /All agents/ }))
  await userEvent.click(screen.getByRole('option', { name: 'Triage' }))
  expect(screen.getByText(/Ranked the Ram Nagar SOS first/)).toBeInTheDocument()
  expect(screen.queryByText(/Merged 3 Reports/)).toBeNull()
  expect(screen.getByRole('button', { name: 'Triage' })).toHaveAttribute('aria-haspopup', 'listbox')
})

test('commander items render as a question and answer card', async () => {
  const extra: FeedItem[] = [
    { kind: 'commander', id: 'q1', time: null, question: 'What changed?', answer: 'Pump 2 is waiting.', streaming: false },
  ]
  render(<ActivityPanel extra={extra} />, { wrapper: providers() })
  const q = await screen.findByText('What changed?')
  expect(within(q.closest('li')!).getByText('Pump 2 is waiting.')).toBeInTheDocument()
})
