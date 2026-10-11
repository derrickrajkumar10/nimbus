import * as maplibregl from 'maplibre-gl'
import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useConsoleData, type ConsoleData } from '../../data/queries'
import { circlePolygon, segmentMidpoint, segmentsToGeoJSON } from '../../domain/geo'
import { noGoRadius } from '../../domain/sos'
import { useSelection, type MapTarget } from '../../state/selection'
import { useShortcuts } from '../../state/shortcuts'
import { STYLE_URL, recolourBasemap } from './basemap'
import { Inspector } from './Inspector'
import { EMPTY_DATA, addNimbusLayers, setLayerVisible, updateNimbusData, type LayerKey, type NimbusLayerData } from './layers'
import { LayerToggles, Legend } from './MapOverlays'
import { hazardPin, resourcePin, sosPin } from './pins'
import './map.css'
import s from './MapView.module.css'

type LngLat = [number, number]

const ALL_ON: Record<LayerKey, boolean> = { risk: true, readings: true, hazards: true, resources: true, sos: true }
const FOCUS_ZOOM = 17.2

function locate(t: MapTarget, d: ConsoleData): LngLat | null {
  const at = (p?: { lat: number; lon: number }): LngLat | null => (p ? [p.lon, p.lat] : null)
  switch (t.kind) {
    case 'segment': {
      const seg = d.segments.find((x) => x.segment_id === t.id)
      return seg ? segmentMidpoint(seg) : null
    }
    case 'hazard':
      return at(d.hazards.find((x) => x.hazard_id === t.id)?.location)
    case 'resource':
      return at(d.resources.find((x) => x.resource_id === t.id)?.location)
    case 'sos':
      return at(d.sos.find((x) => x.sos_id === t.id)?.location)
  }
}

export function MapView() {
  const data = useConsoleData()
  const { target, inspect } = useSelection()
  const container = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const popupRef = useRef<maplibregl.Popup | null>(null)
  const markers = useRef<maplibregl.Marker[]>([])
  const flownTo = useRef<string | null>(null)
  const fitted = useRef(false)
  const inspectRef = useRef(inspect)
  const [ready, setReady] = useState(false)
  const [visible, setVisible] = useState(ALL_ON)
  const [popupNode] = useState(() => document.createElement('div'))

  useEffect(() => {
    inspectRef.current = inspect
  })

  useShortcuts({ Escape: () => inspect(null) })

  // Create the map once.
  useEffect(() => {
    const map = new maplibregl.Map({
      container: container.current!,
      style: STYLE_URL,
      center: [80.2195, 12.975],
      zoom: 15,
      attributionControl: { compact: true },
    })
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right')
    map.on('load', () => {
      recolourBasemap(map)
      addNimbusLayers(map, EMPTY_DATA)
      setReady(true)
    })
    map.on('click', 'seg', (e: maplibregl.MapLayerMouseEvent) => {
      const id = e.features?.[0]?.properties?.segment_id
      if (typeof id === 'string') inspectRef.current({ kind: 'segment', id })
    })
    map.on('mouseenter', 'seg', () => (map.getCanvas().style.cursor = 'pointer'))
    map.on('mouseleave', 'seg', () => (map.getCanvas().style.cursor = ''))

    // Opens to the right of the point; the camera shifts left so it fits on short screens.
    const popup = new maplibregl.Popup({ offset: 16, maxWidth: '300px', className: 'nimbus-popup', closeOnClick: false, anchor: 'left' })
    popup.setDOMContent(popupNode)
    popup.on('close', () => inspectRef.current(null))

    mapRef.current = map
    popupRef.current = popup
    return () => {
      map.remove()
      mapRef.current = null
    }
  }, [popupNode])

  const layerData = useMemo<NimbusLayerData>(
    () => ({
      segments: segmentsToGeoJSON(data.segments, data.risk),
      nogo: {
        type: 'FeatureCollection',
        features: data.hazards.filter((h) => h.status !== 'cleared').map((h) => circlePolygon(h.location, noGoRadius(h))),
      },
    }),
    [data.segments, data.risk, data.hazards],
  )

  useEffect(() => {
    if (ready && mapRef.current) updateNimbusData(mapRef.current, layerData)
  }, [ready, layerData])

  // Frame the ward once Segments arrive.
  useEffect(() => {
    const map = mapRef.current
    if (!ready || !map || fitted.current || data.segments.length === 0) return
    fitted.current = true
    const coords = data.segments.flatMap((sg) => sg.geometry.coordinates)
    const lons = coords.map((c) => c[0])
    const lats = coords.map((c) => c[1])
    map.fitBounds(
      [
        [Math.min(...lons), Math.min(...lats)],
        [Math.max(...lons), Math.max(...lats)],
      ],
      { padding: 60, duration: 0 },
    )
  }, [ready, data.segments])

  useEffect(() => {
    const map = mapRef.current
    if (!ready || !map) return
    for (const key of Object.keys(visible) as LayerKey[]) setLayerVisible(map, key, visible[key])
  }, [ready, visible])

  // Pins: rebuilt when their data or visibility changes.
  useEffect(() => {
    const map = mapRef.current
    if (!ready || !map) return
    markers.current.forEach((m) => m.remove())
    const next: maplibregl.Marker[] = []
    const add = (el: HTMLElement, at: LngLat, t: MapTarget) => {
      el.addEventListener('click', (e) => {
        e.stopPropagation()
        inspectRef.current(t)
      })
      next.push(new maplibregl.Marker({ element: el }).setLngLat(at).addTo(map))
    }
    if (visible.hazards) {
      data.hazards
        .filter((h) => h.status !== 'cleared')
        .forEach((h) => add(hazardPin(h), [h.location.lon, h.location.lat], { kind: 'hazard', id: h.hazard_id }))
    }
    if (visible.resources) {
      data.resources.forEach((r) => add(resourcePin(r), [r.location.lon, r.location.lat], { kind: 'resource', id: r.resource_id }))
    }
    if (visible.sos) {
      data.sos.forEach((c) => add(sosPin(c), [c.location.lon, c.location.lat], { kind: 'sos', id: c.sos_id }))
    }
    markers.current = next
  }, [ready, data.hazards, data.resources, data.sos, visible.hazards, visible.resources, visible.sos])

  // Fly to and open whatever is being inspected.
  useEffect(() => {
    const map = mapRef.current
    const popup = popupRef.current
    if (!ready || !map || !popup) return
    if (!target) {
      flownTo.current = null
      if (popup.isOpen()) popup.remove()
      return
    }
    const key = `${target.kind}:${target.id}`
    if (flownTo.current === key) return
    const at = locate(target, data)
    if (!at) return
    flownTo.current = key
    map.flyTo({ center: at, zoom: FOCUS_ZOOM, speed: 1.4, offset: [-160, 0] })
    popup.setLngLat(at).addTo(map)
  }, [ready, target, data])

  return (
    <div className={s.map}>
      <div ref={container} className={s.canvas} />
      <LayerToggles visible={visible} onToggle={(k) => setVisible((v) => ({ ...v, [k]: !v[k] }))} />
      <Legend />
      {target && createPortal(<Inspector target={target} data={data} showReadings={visible.readings} />, popupNode)}
    </div>
  )
}
