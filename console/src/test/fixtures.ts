// Typed views of contracts/fixtures for tests.
import hazardsJson from '@contracts/fixtures/hazards.json'
import proposalsJson from '@contracts/fixtures/proposals.json'
import readingsJson from '@contracts/fixtures/readings.json'
import resourcesJson from '@contracts/fixtures/resources.json'
import riskJson from '@contracts/fixtures/risk.json'
import segmentsJson from '@contracts/fixtures/segments.json'
import sosJson from '@contracts/fixtures/sos.json'
import type {
  Hazard,
  Proposal,
  Reading,
  Resource1 as Resource,
  Segment,
  SegmentRisk,
  Sos,
} from '@contracts/generated/ts/nimbus'

export const segments = segmentsJson as unknown as Segment[]
export const risk = riskJson as unknown as SegmentRisk[]
export const readings = readingsJson as unknown as Reading[]
export const hazards = hazardsJson as unknown as Hazard[]
export const resources = resourcesJson as unknown as Resource[]
export const sos = sosJson as unknown as Sos[]
export const proposals = proposalsJson as unknown as Proposal[]
