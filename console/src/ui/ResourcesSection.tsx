import type { ResourceStatus } from '@contracts/generated/ts/nimbus'
import { useConsoleData } from '../data/queries'
import { nearestSegment, streetName } from '../domain/geo'
import { useSelection } from '../state/selection'
import { PanelSection } from './PanelSection'
import s from './ListRow.module.css'

const STATUS: Record<ResourceStatus, { label: string; className: string }> = {
  free: { label: 'Free', className: s.free },
  en_route: { label: 'En route', className: s.enRoute },
  working: { label: 'Working', className: s.working },
}

export function ResourcesSection() {
  const { resources, segments } = useConsoleData()
  const { inspect } = useSelection()
  const free = resources.filter((r) => r.status === 'free').length

  return (
    <PanelSection title="Resources" hint={resources.length ? `${free} of ${resources.length} free` : undefined}>
      {resources.map((r) => {
        const seg = nearestSegment(r.location, segments)
        const status = STATUS[r.status]
        return (
          <button key={r.resource_id} className={s.row} onClick={() => inspect({ kind: 'resource', id: r.resource_id })}>
            <span>
              {r.label}
              {seg && <span className={s.sub}>Near {streetName(seg)}</span>}
            </span>
            <span className={`${s.tag} ${status.className}`}>{status.label}</span>
          </button>
        )
      })}
    </PanelSection>
  )
}
