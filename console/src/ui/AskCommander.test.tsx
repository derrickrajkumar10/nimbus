import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../App'
import { providers } from '../test/render'

vi.mock('maplibre-gl', async () => (await import('../test/maplibre')).maplibreMock())

test('/ focuses the input and A typed there does not approve', async () => {
  render(<App />, { wrapper: providers() })
  await screen.findByRole('article', { name: 'Send Pump 2 to Velachery Main Road' })
  await userEvent.keyboard('/')
  const input = screen.getByLabelText('Ask the Commander')
  expect(input).toHaveFocus()
  await userEvent.keyboard('a')
  expect(input).toHaveValue('a')
  expect(screen.queryByText(/Approved by/)).toBeNull()
})

test('submitting shows the question and streamed answer in the feed, input disabled until done', async () => {
  render(<App />, { wrapper: providers() })
  await screen.findByRole('article', { name: 'Send Pump 2 to Velachery Main Road' })
  const input = screen.getByLabelText('Ask the Commander')
  await userEvent.type(input, 'What changed in the last hour?{Enter}')
  expect(input).toBeDisabled()
  expect(await screen.findByText('What changed in the last hour?')).toBeInTheDocument()
  await waitFor(() => expect(input).toBeEnabled(), { timeout: 4000 })
  expect(screen.getByText(/Decisions are waiting for you/)).toBeInTheDocument()
  expect(input).toHaveValue('')
})
