import { QueryClient } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { readConfig, type Config } from '../config'
import { SourceProvider } from '../data/SourceProvider'
import type { NimbusSource } from '../data/source'
import { useSelection } from '../state/selection'
import { SelectionProvider } from '../state/SelectionProvider'
import { fakeSource } from './fakeSource'

/** Shows the inspected map target as "kind:id" so tests can read it. */
export function SelectionProbe() {
  const { target, proposalId } = useSelection()
  return (
    <output data-testid="probe" data-proposal={proposalId ?? ''}>
      {target ? `${target.kind}:${target.id}` : ''}
    </output>
  )
}

export function testConfig(overrides: Partial<Config> = {}): Config {
  return { ...readConfig({}, ''), ...overrides }
}

/** A wrapper with a fresh QueryClient, for render() and renderHook(). */
export function providers(source: NimbusSource = fakeSource(), config: Config = testConfig()) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity } } })
  return function Providers({ children }: { children: ReactNode }) {
    return (
      <SourceProvider source={source} config={config} client={client}>
        <SelectionProvider>{children}</SelectionProvider>
      </SourceProvider>
    )
  }
}
