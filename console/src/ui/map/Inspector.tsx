import type { ReactNode } from 'react'
import type { ConsoleData } from '../../data/queries'
import { BAND_COLOR, BAND_LABEL, bandForScore } from '../../domain/bands'
import { nearestSegment, streetName } from '../../domain/geo'
import { HAZARD_LABEL, OWNER_LABEL, noGoRadius, sosFlagsText } from '../../domain/sos'
import { hhmm, minutesBetween } from '../../domain/time'
import type { MapTarget } from '../../state/selection'
import s from './Inspector.module.css'

const KIND_LABEL = { pump: 'Pump', desilting_crew: 'Desilting crew', tree_crew: 'Tree crew' } as const
const STATUS_LABEL = { free: 'Free', en_route: 'En route', working: 'Working' } as const
const HAZARD_STATUS = { open: 'Open', acknowledged: 'Acknowledged', cleared: 'Cleared' } as const

export function Inspector(props: { target: MapTarget; data: ConsoleData; showReadings: boolean }) {
  const { target, data } = props
  switch (target.kind) {
    case 'segment':
      return <SegmentInspector id={target.id} data={data} showReadings={props.showReadings} />
    case 'hazard': {
      const h = data.hazards.find((x) => x.hazard_id === target.id)
      if (!h) return <Gone />
      return (
        <Card title={HAZARD_LABEL[h.hazard_class]} sub={`Hazard ${h.hazard_id}`}>
          <Stats
            items={[
              [OWNER_LABEL[h.owner], 'owner'],
              [HAZARD_STATUS[h.status], 'status'],
            ]}
          />
          <p className={s.line}>Detected {hhmm(h.detected_at)}</p>
          <p className={s.line}>No-go {noGoRadius(h)} m</p>
        </Card>
      )
    }
    case 'resource': {
      const r = data.resources.find((x) => x.resource_id === target.id)
      if (!r) return <Gone />
      const seg = nearestSegment(r.location, data.segments)
      return (
        <Card title={r.label} sub={KIND_LABEL[r.kind]}>
          <Stats items={[[STATUS_LABEL[r.status], 'status']]} />
          {seg && <p className={s.line}>Near {streetName(seg)}</p>}
        </Card>
      )
    }
    case 'sos': {
      const c = data.sos.find((x) => x.sos_id === target.id)
      if (!c) return <Gone />
      const flags = sosFlagsText(c.flags)
      return (
        <Card title={`SOS · ${c.people_count} people`} sub={c.rank ? `Ranked ${c.rank} by Triage` : 'Not ranked yet'}>
          {flags && <p className={s.line}>{flags}</p>}
          {data.clock && <p className={s.line}>Waiting {minutesBetween(c.created_at, data.clock)} min</p>}
          {c.reasons && c.reasons.length > 0 && (
            <ol className={s.reasons}>
              {c.reasons.map((r) => (
                <li key={r.code}>{r.text}</li>
              ))}
            </ol>
          )}
        </Card>
      )
    }
  }
}

function SegmentInspector({ id, data, showReadings }: { id: string; data: ConsoleData; showReadings: boolean }) {
  const seg = data.segments.find((x) => x.segment_id === id)
  if (!seg) return <Gone />
  const risk = data.risk.find((r) => r.segment_id === id)
  const observed = risk?.band === 'flooded' && showReadings
  const band = risk ? (risk.band === 'flooded' && !showReadings ? bandForScore(risk.score) : risk.band) : 'low'
  const reading = observed
    ? data.readings.filter((r) => r.segment_id === id).sort((a, b) => Date.parse(b.observed_at) - Date.parse(a.observed_at))[0]
    : undefined
  const toFlood =
    risk?.band === 'flooded' ? 'Now' : risk?.minutes_to_flood != null ? `${risk.minutes_to_flood} min` : '—'

  return (
    <Card title={streetName(seg)} sub={`Segment ${seg.segment_id}`}>
      <span className={s.band} style={{ color: BAND_COLOR[band] }}>
        <i style={{ background: BAND_COLOR[band] }} />
        {observed ? 'Flooded · Reading' : BAND_LABEL[band]}
      </span>
      {risk && (
        <Stats
          items={[
            [String(risk.score), 'Risk Score'],
            [toFlood, 'to flood'],
            [String(risk.flood_threshold_mm), 'mm threshold'],
          ]}
        />
      )}
      {reading && (
        <p className={s.reading}>
          <i />
          Reading: {reading.depth.replace('_', ' ')}-deep · confidence {reading.confidence} · {reading.report_ids.length} Reports
        </p>
      )}
      {risk && risk.reasons.length > 0 && (
        <ol className={s.reasons}>
          {risk.reasons.map((r) => (
            <li key={r.code}>{r.text}</li>
          ))}
        </ol>
      )}
    </Card>
  )
}

function Card({ title, sub, children }: { title: string; sub: string; children: ReactNode }) {
  return (
    <div className={s.ins}>
      <h4 className={s.title}>{title}</h4>
      <div className={`${s.sub} num`}>{sub}</div>
      {children}
    </div>
  )
}

function Stats({ items }: { items: [string, string][] }) {
  return (
    <div className={`${s.stats} num`}>
      {items.map(([value, label]) => (
        <div key={label}>
          <b>{value}</b>
          <span>{label}</span>
        </div>
      ))}
    </div>
  )
}

function Gone() {
  return <p className={s.line}>No longer in this Run.</p>
}
