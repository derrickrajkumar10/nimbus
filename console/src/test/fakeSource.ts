import { createFixtureCommander } from '../data/fixtureCommander'
import { createFixtureSource } from '../data/fixtureSource'
import type { NimbusSource } from '../data/source'

/** The fixture source with some calls swapped out. The Commander streams fast. */
export function fakeSource(
  overrides: Partial<NimbusSource> = {},
  opts: { decidedBy?: Record<string, string> } = {},
): NimbusSource {
  return { ...createFixtureSource({ ...opts, commander: createFixtureCommander({ delayMs: 2 }) }), ...overrides }
}
