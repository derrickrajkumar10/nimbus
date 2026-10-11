// HTML pins for the map. Never set `position` on the root element: MapLibre
// positions markers absolutely, and overriding it misplaces every pin.
import type { Hazard, Resource1 as Resource } from '@contracts/generated/ts/nimbus'
import type { SosRow } from '../../data/source'
import { HAZARD_LABEL } from '../../domain/sos'

const PUMP =
  '<svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true"><path d="M7 2c2 2.6 3.5 4.4 3.5 6.2A3.5 3.5 0 0 1 3.5 8.2C3.5 6.4 5 4.6 7 2z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>'
const CREW =
  '<svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true"><path d="M7 1.8l4 5.2H8.6l2.4 3.4H3l2.4-3.4H3z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M7 10.4v2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>'

const escape = (t: string) => t.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!)

function root(kind: string, label: string, inner: string): HTMLElement {
  const el = document.createElement('button')
  el.type = 'button'
  el.className = 'pin'
  el.dataset.pin = kind
  el.setAttribute('aria-label', label)
  el.innerHTML = `${inner}<span class="pin-lbl">${escape(label)}</span>`
  return el
}

export function hazardPin(h: Hazard): HTMLElement {
  return root('hazard', HAZARD_LABEL[h.hazard_class], '<span class="pin-haz"><span>!</span></span>')
}

export function resourcePin(r: Resource): HTMLElement {
  const status = r.status === 'free' ? '' : r.status === 'working' ? ' · working' : ' · en route'
  return root('resource', `${r.label}${status}`, `<span class="pin-res pin-${r.status}">${r.kind === 'pump' ? PUMP : CREW}</span>`)
}

export function sosPin(c: SosRow): HTMLElement {
  return root('sos', `SOS · ${c.people_count} people`, `<span class="pin-sos num">${c.people_count}</span>`)
}
