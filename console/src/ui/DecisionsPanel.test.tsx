import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DecisionError } from '../data/source'
import { fakeSource } from '../test/fakeSource'
import { SelectionProbe, providers } from '../test/render'
import { DecisionsPanel } from './DecisionsPanel'

const WORK_ORDER = 'Send Pump 2 to Velachery Main Road'
const WARD_ALERT = 'Ward Alert to everyone in Velachery'

function setup(source = fakeSource()) {
  render(
    <>
      <DecisionsPanel />
      <SelectionProbe />
    </>,
    { wrapper: providers(source) },
  )
  return source
}

const card = (name: string) => screen.getByRole('article', { name })

test('renders both fixture Proposals in rank order with the Work Order facts', async () => {
  setup()
  await screen.findByRole('article', { name: WORK_ORDER })
  const titles = screen.getAllByRole('heading', { level: 3 }).map((h) => h.textContent)
  expect(titles).toEqual([WORK_ORDER, WARD_ALERT])
  const wo = within(card(WORK_ORDER))
  expect(wo.getByText('17')).toBeInTheDocument()
  expect(wo.getByText('Knee')).toBeInTheDocument()
  expect(wo.getByText('Dispatcher · 02:00')).toBeInTheDocument()
  const wa = within(card(WARD_ALERT))
  expect(wa.getByText('Held by Cedar')).toBeInTheDocument()
  expect(wa.getByText(/முழங்கால்/)).toHaveAttribute('lang', 'ta')
})

test('approve shows the confirmation line and drops the count', async () => {
  setup()
  await screen.findByRole('article', { name: WORK_ORDER })
  const heading = screen.getByRole('heading', { name: /Decisions/ })
  expect(within(heading).getByText('2')).toBeInTheDocument()
  await userEvent.click(within(card(WORK_ORDER)).getByRole('button', { name: 'Approve' }))
  expect(await screen.findByText('Approved by K. Priya · Pump 2 en route')).toBeInTheDocument()
  expect(within(heading).getByText('1')).toBeInTheDocument()
})

test('A approves the selected card', async () => {
  setup()
  await screen.findByRole('article', { name: WORK_ORDER })
  await waitFor(() => expect(screen.getByTestId('probe')).toHaveAttribute('data-proposal', 'pr-0001'))
  await userEvent.keyboard('a')
  expect(await screen.findByText('Approved by K. Priya · Pump 2 en route')).toBeInTheDocument()
})

test('reject asks first', async () => {
  setup()
  await screen.findByRole('article', { name: WORK_ORDER })
  const wo = within(card(WORK_ORDER))
  await userEvent.click(wo.getByRole('button', { name: 'Reject' }))
  expect(wo.getByText('Reject this Proposal?')).toBeInTheDocument()
  await userEvent.click(wo.getByRole('button', { name: 'Cancel' }))
  expect(wo.getByRole('button', { name: 'Approve' })).toBeInTheDocument()
  await userEvent.click(wo.getByRole('button', { name: 'Reject' }))
  await userEvent.click(wo.getByRole('button', { name: 'Reject' }))
  expect(await screen.findByText('Rejected by K. Priya')).toBeInTheDocument()
})

test('editing a Work Order offers only free pumps', async () => {
  setup()
  await screen.findByRole('article', { name: WORK_ORDER })
  const wo = within(card(WORK_ORDER))
  await userEvent.click(wo.getByRole('button', { name: 'Edit' }))
  const options = within(wo.getByLabelText('Resource')).getAllByRole('option').map((o) => o.textContent)
  expect(options).toEqual(['Pump 2'])
})

test('editing a Ward Alert posts edited text', async () => {
  const source = fakeSource()
  const decide = vi.spyOn(source, 'decide')
  setup(source)
  await screen.findByRole('article', { name: WARD_ALERT })
  const wa = within(card(WARD_ALERT))
  await userEvent.click(wa.getByRole('button', { name: 'Edit' }))
  const english = wa.getByLabelText('English')
  await userEvent.clear(english)
  await userEvent.type(english, 'Avoid Velachery Main Road.')
  await userEvent.click(wa.getByRole('button', { name: 'Save and approve' }))
  await waitFor(() => expect(decide).toHaveBeenCalled())
  expect(decide.mock.calls[0][2]).toMatchObject({
    decision: 'edited',
    action: { kind: 'ward_alert', message_en: 'Avoid Velachery Main Road.' },
  })
  expect(await screen.findByText('Edited and approved by K. Priya · Ward Alert sending')).toBeInTheDocument()
})

test('a Proposal decided by another officer leaves the queue', async () => {
  setup(fakeSource({}, { decidedBy: { 'pr-0001': 'officer-2' } }))
  await screen.findByRole('article', { name: WARD_ALERT })
  expect(screen.queryByRole('article', { name: WORK_ORDER })).toBeNull()
})

test('409 on approve shows who decided first', async () => {
  const source = fakeSource({
    decide: () =>
      Promise.reject(new DecisionError('already_decided', 'x', { current_status: 'approved', decided_by: 'officer-2' })),
  })
  setup(source)
  await screen.findByRole('article', { name: WORK_ORDER })
  await userEvent.click(within(card(WORK_ORDER)).getByRole('button', { name: 'Approve' }))
  expect(await screen.findByText('Already approved by officer-2')).toBeInTheDocument()
  expect(screen.queryByText(/en route/)).toBeNull()
})

test('event_not_sent offers retry', async () => {
  const decide = vi.fn().mockRejectedValue(new DecisionError('event_not_sent', 'x'))
  setup(fakeSource({ decide }))
  await screen.findByRole('article', { name: WORK_ORDER })
  await userEvent.click(within(card(WORK_ORDER)).getByRole('button', { name: 'Approve' }))
  expect(await screen.findByText("Saved, but the alert didn't go out.")).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
})

test('other errors restore the buttons with a message', async () => {
  setup(fakeSource({ decide: () => Promise.reject(new DecisionError('network', 'offline')) }))
  await screen.findByRole('article', { name: WORK_ORDER })
  await userEvent.click(within(card(WORK_ORDER)).getByRole('button', { name: 'Approve' }))
  expect(await screen.findByText("Couldn't send. Try again.")).toBeInTheDocument()
  expect(within(card(WORK_ORDER)).getByRole('button', { name: 'Approve' })).toBeInTheDocument()
})

test('decided Proposals collapse into a Decided row', async () => {
  setup(fakeSource({}, { decidedBy: { 'pr-0001': 'officer-2' } }))
  await userEvent.click(await screen.findByRole('button', { name: 'Decided (1)' }))
  expect(screen.getByText(WORK_ORDER)).toBeInTheDocument()
  expect(screen.getByText('Approved by officer-2 · Pump 2 en route')).toBeInTheDocument()
})

test('empty state', async () => {
  setup(fakeSource({ proposals: async () => [] }))
  expect(await screen.findByText('Nothing needs you right now.')).toBeInTheDocument()
})

test('selecting a Work Order inspects its Segment', async () => {
  setup()
  await waitFor(() => expect(screen.getByTestId('probe')).toHaveTextContent('segment:27480309-1'))
  await userEvent.click(card(WARD_ALERT))
  expect(screen.getByTestId('probe')).toHaveAttribute('data-proposal', 'pr-0002')
  expect(screen.getByTestId('probe')).toHaveTextContent('segment:27480309-1')
})
