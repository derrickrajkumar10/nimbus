import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useEffect } from 'react'
import { useSelection } from '../../state/selection'
import { FakeMap, FakeMarker } from '../../test/maplibre'
import { SelectionProbe, providers } from '../../test/render'
import { MapView } from './MapView'

vi.mock('maplibre-gl', async () => (await import('../../test/maplibre')).maplibreMock())

function Select({ id }: { id: string }) {
  const { inspect } = useSelection()
  useEffect(() => inspect({ kind: 'segment', id }), [id, inspect])
  return null
}

const map = () => FakeMap.instances.at(-1)!

beforeEach(() => {
  FakeMap.instances = []
  FakeMarker.instances = []
})

test('MapView adds Nimbus sources and layers after load', async () => {
  render(<MapView />, { wrapper: providers() })
  await waitFor(() => expect(map().layers.has('seg')).toBe(true))
  expect(map().callsTo('addSource').map((a) => a[0])).toEqual(['segments', 'nogo'])
  expect([...map().layers.keys()]).toEqual(['nogo-fill', 'nogo-line', 'seg-case', 'seg'])
  await waitFor(() => expect((map().getSource('segments')!.data as { features: unknown[] }).features).toHaveLength(21))
})

test('MapView places a pin for every hazard, resource and SOS', async () => {
  render(<MapView />, { wrapper: providers() })
  await waitFor(() => expect(FakeMarker.instances.length).toBe(5))
})

test('MapView flies to the selected Work Order Segment and opens the inspector', async () => {
  render(
    <>
      <Select id="27480309-1" />
      <MapView />
    </>,
    { wrapper: providers() },
  )
  await waitFor(() => expect(map().callsTo('flyTo')).toHaveLength(1))
  const [{ center }] = map().callsTo('flyTo')[0] as [{ center: [number, number] }]
  expect(center[0]).toBeCloseTo(80.2212, 3)
  expect(center[1]).toBeGreaterThan(12.9775)
  expect(center[1]).toBeLessThan(12.9778)
  expect(await screen.findByText('Flooded · Reading')).toBeInTheDocument()
})

function InspectButton({ target }: { target: { kind: 'resource'; id: string } }) {
  const { inspect } = useSelection()
  return <button onClick={() => inspect(target)}>inspect {target.id}</button>
}

test('inspecting a second target switches the open inspector to it', async () => {
  render(
    <>
      <Select id="27480309-1" />
      <InspectButton target={{ kind: 'resource', id: 'rs-pump-2' }} />
      <MapView />
      <SelectionProbe />
    </>,
    { wrapper: providers() },
  )
  await screen.findByText('Flooded · Reading')
  await userEvent.click(screen.getByRole('button', { name: 'inspect rs-pump-2' }))
  expect(await screen.findByRole('heading', { name: 'Pump 2' })).toBeInTheDocument()
  expect(screen.getByTestId('probe')).toHaveTextContent('resource:rs-pump-2')
})

test('clicking a Segment line inspects it', async () => {
  render(
    <>
      <MapView />
      <SelectionProbe />
    </>,
    { wrapper: providers() },
  )
  await waitFor(() => expect(map().layers.has('seg')).toBe(true))
  act(() => map().fire('click', 'seg', { features: [{ properties: { segment_id: '27320162-1' } }] }))
  expect(screen.getByTestId('probe')).toHaveTextContent('segment:27320162-1')
})

test('Escape closes the inspector', async () => {
  render(
    <>
      <Select id="27480309-1" />
      <MapView />
      <SelectionProbe />
    </>,
    { wrapper: providers() },
  )
  await screen.findByText('Flooded · Reading')
  await userEvent.keyboard('{Escape}')
  expect(screen.getByTestId('probe')).toHaveTextContent('')
})

test('toggling Risk hides seg and seg-case', async () => {
  render(<MapView />, { wrapper: providers() })
  await waitFor(() => expect(map().layers.has('seg')).toBe(true))
  await userEvent.click(screen.getByRole('button', { name: 'Risk' }))
  expect(screen.getByRole('button', { name: 'Risk' })).toHaveAttribute('aria-pressed', 'false')
  const calls = map().callsTo('setLayoutProperty')
  expect(calls).toContainEqual(['seg', 'visibility', 'none'])
  expect(calls).toContainEqual(['seg-case', 'visibility', 'none'])
})

test('toggling SOS removes the SOS pin', async () => {
  render(<MapView />, { wrapper: providers() })
  await waitFor(() => expect(document.querySelectorAll('[data-pin="sos"]')).toHaveLength(1))
  await userEvent.click(screen.getByRole('button', { name: 'SOS' }))
  expect(document.querySelectorAll('[data-pin="sos"]')).toHaveLength(0)
})
