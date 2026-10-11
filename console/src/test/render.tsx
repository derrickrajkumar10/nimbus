import { QueryClient } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { readConfig, type Config } from '../config'
import { SourceProvider } from '../data/SourceProvider'
import type { NimbusSource } from '../data/source'
import { fakeSource } from './fakeSource'

export function testConfig(overrides: Partial<Config> = {}): Config {
  return { ...readConfig({}, ''), ...overrides }
}

/** A wrapper with a fresh QueryClient, for render() and renderHook(). */
export function providers(source: NimbusSource = fakeSource(), config: Config = testConfig()) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity } } })
  return function Providers({ children }: { children: ReactNode }) {
    return (
      <SourceProvider source={source} config={config} client={client}>
        {children}
      </SourceProvider>
    )
  }
}
