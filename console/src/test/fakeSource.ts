import { createFixtureSource } from '../data/fixtureSource'
import type { NimbusSource } from '../data/source'

/** The fixture source with some calls swapped out. */
export function fakeSource(
  overrides: Partial<NimbusSource> = {},
  opts: { decidedBy?: Record<string, string> } = {},
): NimbusSource {
  return { ...createFixtureSource(opts), ...overrides }
}
