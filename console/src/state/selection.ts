import { createContext, useContext } from 'react'

export type MapTarget = { kind: 'segment' | 'hazard' | 'resource' | 'sos'; id: string }

export type Selection = {
  proposalId: string | null
  selectProposal(id: string | null): void
  target: MapTarget | null
  inspect(t: MapTarget | null): void
}

export const SelectionContext = createContext<Selection | null>(null)

export function useSelection(): Selection {
  const s = useContext(SelectionContext)
  if (!s) throw new Error('SelectionProvider is missing')
  return s
}
