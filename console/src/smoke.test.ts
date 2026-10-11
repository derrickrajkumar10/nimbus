import risk from '@contracts/fixtures/risk.json'
import type { SegmentRisk } from '@contracts/generated/ts/nimbus'

test('contracts alias resolves fixtures and types', () => {
  const rows = risk as SegmentRisk[]
  expect(rows.find((r) => r.segment_id === '27480309-1')?.band).toBe('flooded')
})
