import type { LayerKey } from './layers'
import s from './MapOverlays.module.css'

const TOGGLES: [LayerKey, string][] = [
  ['risk', 'Risk'],
  ['readings', 'Readings'],
  ['hazards', 'Hazards'],
  ['resources', 'Resources'],
  ['sos', 'SOS'],
]

export function LayerToggles(props: { visible: Record<LayerKey, boolean>; onToggle(key: LayerKey): void }) {
  return (
    <div className={s.layers} role="group" aria-label="Map layers">
      {TOGGLES.map(([key, label]) => (
        <button key={key} aria-pressed={props.visible[key]} onClick={() => props.onToggle(key)}>
          {label}
        </button>
      ))}
    </div>
  )
}

export function Legend() {
  return (
    <div className={s.legend} aria-label="Legend">
      <span>
        <i style={{ background: 'var(--water)' }} />
        Flooded
      </span>
      <span>
        <i style={{ background: 'var(--likely)' }} />
        Likely
      </span>
      <span>
        <i style={{ background: 'var(--watch)' }} />
        Watch
      </span>
      <span>
        <i style={{ background: 'var(--low)', opacity: 0.55 }} />
        Low
      </span>
    </div>
  )
}
