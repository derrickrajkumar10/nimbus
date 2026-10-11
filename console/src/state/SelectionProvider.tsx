import { useMemo, useState, type ReactNode } from 'react'
import { SelectionContext, type MapTarget, type Selection } from './selection'

export function SelectionProvider({ children }: { children: ReactNode }) {
  const [proposalId, selectProposal] = useState<string | null>(null)
  const [target, inspect] = useState<MapTarget | null>(null)
  const value = useMemo<Selection>(() => ({ proposalId, selectProposal, target, inspect }), [proposalId, target])
  return <SelectionContext.Provider value={value}>{children}</SelectionContext.Provider>
}
