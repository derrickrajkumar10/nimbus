import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { nearestSegment, streetName } from '../domain/geo'
import { fakeSource } from '../test/fakeSource'
import { segments, sos } from '../test/fixtures'
import { SelectionProbe, providers } from '../test/render'
import { ResourcesSection } from './ResourcesSection'
import { SosSection } from './SosSection'

function setup(source = fakeSource()) {
  render(
    <>
      <SosSection />
      <ResourcesSection />
      <SelectionProbe />
    </>,
    { wrapper: providers(source) },
  )
}

test('SOS row reads the fixture call', async () => {
  setup()
  const street = streetName(nearestSegment(sos[0].location, segments)!)
  const row = await screen.findByRole('button', { name: new RegExp(`${street} · 3 people`) })
  expect(within(row).getByText('Elderly resident · waiting 5 min')).toBeInTheDocument()
  expect(within(row).getByText('Open')).toBeInTheDocument()
  await userEvent.click(row)
  expect(screen.getByTestId('probe')).toHaveTextContent('sos:sos-0001')
})

test('Resources show 2 of 3 free with tags', async () => {
  setup()
  expect(await screen.findByText('2 of 3 free')).toBeInTheDocument()
  expect(within(screen.getByRole('button', { name: /Pump 1/ })).getByText('Working')).toBeInTheDocument()
  expect(within(screen.getByRole('button', { name: /Pump 2/ })).getByText('Free')).toBeInTheDocument()
})

test('clicking a resource inspects it', async () => {
  setup()
  await userEvent.click(await screen.findByRole('button', { name: /Pump 2/ }))
  expect(screen.getByTestId('probe')).toHaveTextContent('resource:rs-pump-2')
})

test('en route resources show their own tag', async () => {
  const base = fakeSource()
  setup({
    ...base,
    resources: async (run) => (await base.resources(run)).map((r) => ({ ...r, status: 'en_route' as const })),
  })
  expect(await screen.findAllByText('En route')).toHaveLength(3)
})

test('empty SOS state', async () => {
  setup(fakeSource({ sos: async () => [] }))
  expect(await screen.findByText('No open SOS.')).toBeInTheDocument()
})
