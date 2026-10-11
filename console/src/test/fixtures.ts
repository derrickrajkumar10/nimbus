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
import { MICHAUNG_RAIN, SCENE_EVENTS, SCENE_WARD_ALERT } from '../data/fixtureScene'
import type { ConsoleData } from '../data/queries'

export const segments = segmentsJson as unknown as Segment[]
export const risk = riskJson as unknown as SegmentRisk[]
export const readings = readingsJson as unknown as Reading[]
export const hazards = hazardsJson as unknown as Hazard[]
export const resources = resourcesJson as unknown as Resource[]
export const sos = sosJson as unknown as Sos[]
export const proposals = proposalsJson as unknown as Proposal[]

/** The whole fixture scene as useConsoleData would return it. */
export function fixtureData(overrides: Partial<ConsoleData> = {}): ConsoleData {
  return {
    segments,
    risk,
    readings,
    hazards,
    resources,
    sos,
    proposals: [...proposals, SCENE_WARD_ALERT],
    events: SCENE_EVENTS,
    rain: MICHAUNG_RAIN,
    clock: '2023-12-04T02:00:00+05:30',
    isLoading: false,
    ...overrides,
  }
}
