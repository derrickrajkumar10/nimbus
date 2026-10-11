import { render } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useShortcuts } from './shortcuts'

function Harness({ onA }: { onA: () => void }) {
  useShortcuts({ a: onA })
  return <input aria-label="question" />
}

test('shortcuts fire on keys', async () => {
  const onA = vi.fn()
  render(<Harness onA={onA} />)
  await userEvent.keyboard('a')
  expect(onA).toHaveBeenCalledTimes(1)
  await userEvent.keyboard('A')
  expect(onA).toHaveBeenCalledTimes(2)
})

test('shortcuts ignore typing', async () => {
  const onA = vi.fn()
  const { getByLabelText } = render(<Harness onA={onA} />)
  await userEvent.click(getByLabelText('question'))
  await userEvent.keyboard('a')
  expect(onA).not.toHaveBeenCalled()
})

test('shortcuts ignore modifiers', async () => {
  const onA = vi.fn()
  render(<Harness onA={onA} />)
  await userEvent.keyboard('{Control>}a{/Control}')
  await userEvent.keyboard('{Meta>}a{/Meta}')
  expect(onA).not.toHaveBeenCalled()
})
