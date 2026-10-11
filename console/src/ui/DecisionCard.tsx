import type { Proposal } from '@contracts/generated/ts/nimbus'
import { useState } from 'react'
import { useDecide } from '../data/queries'
import { DecisionError, type DecisionInput } from '../data/source'
import {
  confirmationLine,
  deciderName,
  isWorkOrder,
  proposalTitle,
  workOrderFacts,
  type ProposalContext,
} from '../domain/proposals'
import { hhmm } from '../domain/time'
import { useShortcuts } from '../state/shortcuts'
import { DecisionEditor } from './DecisionEditor'
import { Check } from './icons'
import s from './DecisionCard.module.css'

type Mode =
  | { kind: 'idle' }
  | { kind: 'busy' }
  | { kind: 'editing' }
  | { kind: 'confirmReject' }
  | { kind: 'failed' }
  | { kind: 'conflict'; text: string }
  | { kind: 'notSent'; input: DecisionInput }

type Ctx = ProposalContext & { officerId: string; officerName: string }

const capital = (w: string) => w.charAt(0).toUpperCase() + w.slice(1)

export function DecisionCard(props: {
  proposal: Proposal
  ctx: Ctx
  selected: boolean
  onSelect(): void
  onTouched(): void
}) {
  const { proposal: p, ctx, selected } = props
  const decide = useDecide()
  const [mode, setMode] = useState<Mode>({ kind: 'idle' })
  const pending = (p.status ?? 'pending') === 'pending'
  const title = proposalTitle(p, ctx)
  const action = p.action
  const canAct = pending && (mode.kind === 'idle' || mode.kind === 'failed')

  async function send(input: DecisionInput) {
    props.onTouched()
    setMode({ kind: 'busy' })
    try {
      await decide(p.proposal_id, input)
      setMode({ kind: 'idle' })
    } catch (e) {
      if (e instanceof DecisionError && e.code === 'already_decided') {
        const who = deciderName(e.detail.decided_by, ctx.officerId, ctx.officerName)
        setMode({ kind: 'conflict', text: `Already ${e.detail.current_status ?? 'decided'} by ${who}` })
      } else if (e instanceof DecisionError && e.code === 'event_not_sent') {
        setMode({ kind: 'notSent', input })
      } else {
        setMode({ kind: 'failed' })
      }
    }
  }

  const approve = () => send({ decision: 'approved', decided_by: ctx.officerId })
  const reject = () => send({ decision: 'rejected', decided_by: ctx.officerId })

  useShortcuts(
    selected && canAct
      ? { a: approve, e: () => setMode({ kind: 'editing' }), r: () => setMode({ kind: 'confirmReject' }) }
      : {},
  )

  return (
    <article className={`${s.card} ${selected ? s.selected : ''}`} aria-label={title} onClick={props.onSelect}>
      <div className={s.kick}>
        <span className={s.kind}>{isWorkOrder(action) ? 'Work Order' : 'Ward Alert'}</span>
        {isWorkOrder(action) ? (
          <span className="num">
            {capital(p.proposed_by)} · {hhmm(p.created_at)}
          </span>
        ) : (
          <span className={s.held}>Held by Cedar</span>
        )}
      </div>
      <h3 className={s.title}>{title}</h3>
      <p className={s.reason}>{p.reason}</p>

      {isWorkOrder(action) ? (
        <Facts {...workOrderFacts(action, ctx.readings)} />
      ) : (
        <div className={s.draft}>
          {action.message_en}
          <div lang="ta" className={s.ta}>
            {action.message_ta}
          </div>
        </div>
      )}

      {mode.kind === 'conflict' ? (
        <p className={s.conflict}>{mode.text}</p>
      ) : !pending ? (
        <p className={s.done}>
          <Check color="var(--teal)" />
          {confirmationLine(p, ctx)}
        </p>
      ) : mode.kind === 'editing' ? (
        <DecisionEditor
          proposal={p}
          resources={ctx.resources}
          onCancel={() => setMode({ kind: 'idle' })}
          onSave={(edited) => send({ decision: 'edited', decided_by: ctx.officerId, action: edited })}
        />
      ) : mode.kind === 'confirmReject' ? (
        <div className={s.confirm}>
          <span>Reject this Proposal?</span>
          <button className={s.danger} onClick={reject}>
            Reject
          </button>
          <button className={s.secondary} onClick={() => setMode({ kind: 'idle' })}>
            Cancel
          </button>
        </div>
      ) : mode.kind === 'notSent' ? (
        <div className={s.confirm}>
          <span>Saved, but the alert didn't go out.</span>
          <button className={s.secondary} onClick={() => send(mode.input)}>
            Retry
          </button>
        </div>
      ) : (
        <>
          <div className={s.acts}>
            <button className={s.approve} onClick={approve} disabled={!canAct}>
              Approve
              {selected && <kbd aria-hidden="true">A</kbd>}
            </button>
            <button className={s.secondary} onClick={() => setMode({ kind: 'editing' })} disabled={!canAct}>
              Edit
            </button>
            <button className={s.secondary} onClick={() => setMode({ kind: 'confirmReject' })} disabled={!canAct}>
              Reject
            </button>
          </div>
          {mode.kind === 'failed' && <p className={s.error}>Couldn't send. Try again.</p>}
        </>
      )}
    </article>
  )
}

function Facts({ buildings, depth, reports }: ReturnType<typeof workOrderFacts>) {
  return (
    <div className={`${s.facts} num`}>
      <div>
        <b>{buildings}</b>buildings
      </div>
      <div>
        <b>{depth ? capital(depth.replace('_', ' ')) : '—'}</b>depth
      </div>
      <div>
        <b>{reports}</b>Reports
      </div>
    </div>
  )
}
