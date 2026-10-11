import { useConsoleData } from '../data/queries'
import { nearestSegment, streetName } from '../domain/geo'
import { sosFlagsText } from '../domain/sos'
import { minutesBetween } from '../domain/time'
import { useSelection } from '../state/selection'
import { PanelSection } from './PanelSection'
import s from './ListRow.module.css'

export function SosSection() {
  const { sos, segments, clock, isLoading } = useConsoleData()
  const { inspect } = useSelection()
  const rows = [...sos].sort(
    (a, b) => (a.rank ?? Infinity) - (b.rank ?? Infinity) || Date.parse(a.created_at) - Date.parse(b.created_at),
  )

  return (
    <PanelSection title="SOS" count={sos.length} countTone="sos" hint="Ranked by Triage">
      {rows.map((call) => {
        const seg = nearestSegment(call.location, segments)
        const flags = sosFlagsText(call.flags)
        const waiting = clock ? `waiting ${minutesBetween(call.created_at, clock)} min` : ''
        return (
          <button key={call.sos_id} className={s.row} onClick={() => inspect({ kind: 'sos', id: call.sos_id })}>
            <span>
              {seg ? streetName(seg) : 'Unknown street'} · {call.people_count} people
              <span className={`${s.sub} num`}>{[flags, waiting].filter(Boolean).join(' · ')}</span>
            </span>
            <span className={`${s.tag} ${s.sos}`}>Open</span>
          </button>
        )
      })}
      {!isLoading && rows.length === 0 && <p className={s.empty}>No open SOS.</p>}
    </PanelSection>
  )
}
