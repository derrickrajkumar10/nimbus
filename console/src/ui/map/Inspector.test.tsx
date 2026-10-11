import { render, screen } from '@testing-library/react'
import { fixtureData, risk, segments } from '../../test/fixtures'
import { Inspector } from './Inspector'

const seg = (id: string) => ({ kind: 'segment' as const, id })

test('Inspector for the flooded Segment', () => {
  render(<Inspector target={seg('27480309-1')} data={fixtureData()} showReadings />)
  expect(screen.getByRole('heading', { name: 'Velachery Main Road' })).toBeInTheDocument()
  expect(screen.getByText('Segment 27480309-1')).toBeInTheDocument()
  expect(screen.getByText('Flooded · Reading')).toBeInTheDocument()
  expect(screen.getByText('92')).toBeInTheDocument()
  expect(screen.getByText('Now')).toBeInTheDocument()
  expect(screen.getByText('67.5')).toBeInTheDocument()
  expect(screen.getByText('Reading: knee-deep · confidence 0.82 · 3 Reports')).toBeInTheDocument()
  expect(screen.getAllByRole('listitem')).toHaveLength(3)
})

test('Inspector for a watch Segment with null minutes shows a dash', () => {
  const r = risk.map((x) => (x.segment_id === '27480309-3' ? { ...x, minutes_to_flood: null } : x))
  render(<Inspector target={seg('27480309-3')} data={fixtureData({ risk: r })} showReadings />)
  expect(screen.getByText('—')).toBeInTheDocument()
  expect(screen.getByText('Watch')).toBeInTheDocument()
  expect(screen.queryByText(/Flooded/)).toBeNull()
})

test('Inspector shows minutes to flood when known', () => {
  render(<Inspector target={seg('27480309-3')} data={fixtureData()} showReadings />)
  expect(screen.getByText('60 min')).toBeInTheDocument()
})

test('Inspector falls back to Unnamed road', () => {
  const s = segments.map((x) => (x.segment_id === '27480309-3' ? { ...x, street_name: null } : x))
  render(<Inspector target={seg('27480309-3')} data={fixtureData({ segments: s })} showReadings />)
  expect(screen.getByRole('heading', { name: 'Unnamed road' })).toBeInTheDocument()
})

test('Inspector hides the Reading line when readings are toggled off', () => {
  render(<Inspector target={seg('27480309-1')} data={fixtureData()} showReadings={false} />)
  expect(screen.queryByText(/Reading:/)).toBeNull()
  expect(screen.getByText('Likely')).toBeInTheDocument()
})

test('Inspector for the hazard', () => {
  render(<Inspector target={{ kind: 'hazard', id: 'hz-0001' }} data={fixtureData()} showReadings />)
  expect(screen.getByRole('heading', { name: 'Open manhole' })).toBeInTheDocument()
  expect(screen.getByText('Corporation')).toBeInTheDocument()
  expect(screen.getByText('No-go 30 m')).toBeInTheDocument()
  expect(screen.getByText('Detected 01:50')).toBeInTheDocument()
})

test('Inspector for a resource and an SOS', () => {
  const { unmount } = render(<Inspector target={{ kind: 'resource', id: 'rs-pump-1' }} data={fixtureData()} showReadings />)
  expect(screen.getByRole('heading', { name: 'Pump 1' })).toBeInTheDocument()
  expect(screen.getByText('Working')).toBeInTheDocument()
  unmount()
  render(<Inspector target={{ kind: 'sos', id: 'sos-0001' }} data={fixtureData()} showReadings />)
  expect(screen.getByRole('heading', { name: 'SOS · 3 people' })).toBeInTheDocument()
  expect(screen.getByText('Elderly resident')).toBeInTheDocument()
  expect(screen.getByText('Waiting 5 min')).toBeInTheDocument()
})

test('Inspector for a target that no longer exists says so', () => {
  render(<Inspector target={{ kind: 'hazard', id: 'gone' }} data={fixtureData()} showReadings />)
  expect(screen.getByText('No longer in this Run.')).toBeInTheDocument()
})
