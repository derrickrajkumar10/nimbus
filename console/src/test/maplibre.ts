// A recording stand-in for maplibre-gl; jsdom has no WebGL.
// Use: vi.mock('maplibre-gl', async () => (await import('../test/maplibre')).maplibreMock())

type Handler = (e?: unknown) => void

export class FakeMap {
  static instances: FakeMap[] = []
  calls: { method: string; args: unknown[] }[] = []
  sources = new Map<string, { data: unknown; setData(d: unknown): void }>()
  layers = new Map<string, unknown>()
  handlers: { event: string; layer?: string; fn: Handler }[] = []
  container: HTMLElement

  constructor(opts: { container: HTMLElement }) {
    this.container = opts.container
    FakeMap.instances.push(this)
    setTimeout(() => this.fire('load'), 0)
  }

  private record(method: string, args: unknown[]) {
    this.calls.push({ method, args })
  }

  callsTo(method: string) {
    return this.calls.filter((c) => c.method === method).map((c) => c.args)
  }

  fire(event: string, layer?: string, payload?: unknown) {
    this.handlers.filter((h) => h.event === event && h.layer === layer).forEach((h) => h.fn(payload))
  }

  on(event: string, layerOrFn: string | Handler, fn?: Handler) {
    if (typeof layerOrFn === 'function') this.handlers.push({ event, fn: layerOrFn })
    else this.handlers.push({ event, layer: layerOrFn, fn: fn! })
    return this
  }
  off() {
    return this
  }
  addSource(id: string, spec: { data: unknown }) {
    this.record('addSource', [id, spec])
    const src = { data: spec.data, setData: (d: unknown) => ((src.data = d), this.record('setData', [id, d])) }
    this.sources.set(id, src)
  }
  getSource(id: string) {
    return this.sources.get(id)
  }
  addLayer(spec: { id: string }) {
    this.record('addLayer', [spec])
    this.layers.set(spec.id, spec)
  }
  getLayer(id: string) {
    return this.layers.get(id)
  }
  setPaintProperty(...args: unknown[]) {
    this.record('setPaintProperty', args)
  }
  setLayoutProperty(...args: unknown[]) {
    this.record('setLayoutProperty', args)
  }
  flyTo(...args: unknown[]) {
    this.record('flyTo', args)
  }
  fitBounds(...args: unknown[]) {
    this.record('fitBounds', args)
  }
  addControl(...args: unknown[]) {
    this.record('addControl', args)
  }
  getStyle() {
    return { layers: [] }
  }
  getCanvas() {
    return { style: {} as Record<string, string> }
  }
  isStyleLoaded() {
    return true
  }
  resize() {}
  remove() {
    this.record('remove', [])
  }
}

export class FakeMarker {
  static instances: FakeMarker[] = []
  element: HTMLElement
  lngLat: unknown = null
  constructor(opts: { element: HTMLElement }) {
    this.element = opts.element
    FakeMarker.instances.push(this)
  }
  setLngLat(ll: unknown) {
    this.lngLat = ll
    return this
  }
  addTo(map: FakeMap) {
    map.container.appendChild(this.element)
    return this
  }
  getElement() {
    return this.element
  }
  remove() {
    this.element.remove()
    return this
  }
}

export class FakePopup {
  static instances: FakePopup[] = []
  node: HTMLElement | null = null
  lngLat: unknown = null
  open = false
  handlers: Record<string, Handler[]> = {}
  constructor() {
    FakePopup.instances.push(this)
  }
  setLngLat(ll: unknown) {
    this.lngLat = ll
    return this
  }
  setDOMContent(node: HTMLElement) {
    this.node = node
    return this
  }
  // Like MapLibre 6: re-adding an open popup removes it first, which fires 'close'.
  addTo(map: FakeMap) {
    if (this.open) this.remove()
    this.open = true
    if (this.node) map.container.appendChild(this.node)
    return this
  }
  on(event: string, fn: Handler) {
    ;(this.handlers[event] ??= []).push(fn)
    return this
  }
  off() {
    return this
  }
  isOpen() {
    return this.open
  }
  remove() {
    if (!this.open) return this
    this.open = false
    this.node?.remove()
    ;(this.handlers.close ?? []).forEach((fn) => fn())
    return this
  }
}

export class FakeNavigationControl {}
export class FakeAttributionControl {}

export function maplibreMock() {
  const api = {
    Map: FakeMap,
    Marker: FakeMarker,
    Popup: FakePopup,
    NavigationControl: FakeNavigationControl,
    AttributionControl: FakeAttributionControl,
  }
  return { ...api, default: api }
}
