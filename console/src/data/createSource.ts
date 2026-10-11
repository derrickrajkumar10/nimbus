import type { Config } from '../config'
import { createFixtureSource } from './fixtureSource'
import { createHttpSource } from './httpSource'
import type { NimbusSource } from './source'

/** Fixtures unless VITE_NIMBUS_API is set. */
export function createSource(cfg: Config): NimbusSource {
  return cfg.apiUrl ? createHttpSource(cfg) : createFixtureSource()
}
