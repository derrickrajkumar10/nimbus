import type { Proposal } from '@contracts/generated/ts/nimbus'
import { useEffect, useState } from 'react'
import { useConfig, useConsoleData } from '../data/queries'
import { confirmationLine, isWorkOrder, proposalTitle, splitProposals } from '../domain/proposals'
import { useSelection } from '../state/selection'
import { DecisionCard } from './DecisionCard'
import { Chevron } from './icons'
import { PanelSection } from './PanelSection'
import s from './DecisionsPanel.module.css'

export function DecisionsPanel() {
  const data = useConsoleData()
  const { wardName, officerId, officerName } = useConfig()
  const { proposalId, selectProposal, inspect } = useSelection()
  // Proposals this officer acted on stay in place so the outcome reads on the card.
  const [touched, setTouched] = useState<ReadonlySet<string>>(new Set())
  const [showDecided, setShowDecided] = useState(false)

  const ctx = { resources: data.resources, segments: data.segments, readings: data.readings, wardName, officerId, officerName }
  const { pending, decided } = splitProposals(data.proposals)
  const queue = data.proposals
    .filter((p) => (p.status ?? 'pending') === 'pending' || touched.has(p.proposal_id))
    .sort((a, b) => a.rank - b.rank)
  const archived = decided.filter((p) => !touched.has(p.proposal_id))

  const select = (p: Proposal) => {
    selectProposal(p.proposal_id)
    if (isWorkOrder(p.action)) inspect({ kind: 'segment', id: p.action.segment_id })
  }

  const first = pending[0]
  useEffect(() => {
    if (!proposalId && first) {
      selectProposal(first.proposal_id)
      if (isWorkOrder(first.action)) inspect({ kind: 'segment', id: first.action.segment_id })
    }
  }, [proposalId, first, selectProposal, inspect])

  return (
    <PanelSection title="Decisions" count={pending.length} hint="Ranked by people affected">
      {queue.map((p) => (
        <DecisionCard
          key={p.proposal_id}
          proposal={p}
          ctx={ctx}
          selected={p.proposal_id === proposalId}
          onSelect={() => select(p)}
          onTouched={() => setTouched((t) => new Set(t).add(p.proposal_id))}
        />
      ))}
      {!data.isLoading && queue.length === 0 && <p className={s.empty}>Nothing needs you right now.</p>}
      {archived.length > 0 && (
        <div className={s.decided}>
          <button className={s.toggle} aria-expanded={showDecided} onClick={() => setShowDecided((v) => !v)}>
            Decided ({archived.length})
            <span className={showDecided ? s.open : ''}>
              <Chevron />
            </span>
          </button>
          {showDecided && (
            <ul className={s.list}>
              {archived.map((p) => (
                <li key={p.proposal_id}>
                  <span className={s.itemTitle}>{proposalTitle(p, ctx)}</span>
                  <span className={s.itemLine}>{confirmationLine(p, ctx)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </PanelSection>
  )
}
