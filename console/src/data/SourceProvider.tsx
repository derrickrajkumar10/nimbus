import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useMemo, useState, type ReactNode } from 'react'
import type { Config } from '../config'
import { SourceContext, createInflightStore, createSyncStore, type SourceCtx } from './queries'
import type { NimbusSource } from './source'

export function SourceProvider(props: {
  source: NimbusSource
  config: Config
  client?: QueryClient
  children: ReactNode
}) {
  const { source, config } = props
  const [client] = useState(
    () => props.client ?? new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } } }),
  )
  const ctx = useMemo<SourceCtx>(
    () => ({ source, config, sync: createSyncStore(), inflight: createInflightStore(), activity: new Map() }),
    [source, config],
  )
  return (
    <QueryClientProvider client={client}>
      <SourceContext.Provider value={ctx}>{props.children}</SourceContext.Provider>
    </QueryClientProvider>
  )
}
