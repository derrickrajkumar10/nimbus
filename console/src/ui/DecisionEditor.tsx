import type { Proposal, Resource1 as Resource, WardAlertDraft, WorkOrder } from '@contracts/generated/ts/nimbus'
import { useId, useState } from 'react'
import { isWorkOrder } from '../domain/proposals'
import s from './DecisionCard.module.css'

/** Inline editor: another free Resource of the same kind, or the Ward Alert's text. */
export function DecisionEditor(props: {
  proposal: Proposal
  resources: Resource[]
  onSave(action: WorkOrder | WardAlertDraft): void
  onCancel(): void
}) {
  const { proposal, resources } = props
  const id = useId()
  const action = proposal.action

  const current = isWorkOrder(action) ? resources.find((r) => r.resource_id === action.resource_id) : undefined
  const choices = current
    ? [current, ...resources.filter((r) => r.kind === current.kind && r.status === 'free' && r !== current)]
    : []
  const [resourceId, setResourceId] = useState(isWorkOrder(action) ? action.resource_id : '')
  const [en, setEn] = useState(isWorkOrder(action) ? '' : action.message_en)
  const [ta, setTa] = useState(isWorkOrder(action) ? '' : action.message_ta)

  const save = () =>
    props.onSave(
      isWorkOrder(action)
        ? { ...action, kind: 'work_order', resource_id: resourceId }
        : { ...action, kind: 'ward_alert', message_en: en.trim(), message_ta: ta.trim() },
    )

  return (
    <div className={s.editor}>
      {isWorkOrder(action) ? (
        <label className={s.field} htmlFor={`${id}-r`}>
          <span>Resource</span>
          <select id={`${id}-r`} value={resourceId} onChange={(e) => setResourceId(e.target.value)}>
            {choices.map((r) => (
              <option key={r.resource_id} value={r.resource_id}>
                {r.label}
              </option>
            ))}
          </select>
        </label>
      ) : (
        <>
          <label className={s.field} htmlFor={`${id}-en`}>
            <span>English</span>
            <textarea id={`${id}-en`} rows={2} value={en} onChange={(e) => setEn(e.target.value)} />
          </label>
          <label className={s.field} htmlFor={`${id}-ta`}>
            <span>Tamil</span>
            <textarea id={`${id}-ta`} lang="ta" rows={3} value={ta} onChange={(e) => setTa(e.target.value)} />
          </label>
        </>
      )}
      <div className={s.acts}>
        <button className={s.approve} onClick={save} disabled={!isWorkOrder(action) && (!en.trim() || !ta.trim())}>
          Save and approve
        </button>
        <button className={s.secondary} onClick={props.onCancel}>
          Cancel
        </button>
      </div>
    </div>
  )
}
