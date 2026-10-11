import type { Map as MapLibreMap } from 'maplibre-gl'

export const STYLE_URL = 'https://tiles.openfreemap.org/styles/fiord'

/** Recolour OpenFreeMap fiord to the Deep tide sea so the risk layers carry the colour. */
export function recolourBasemap(map: MapLibreMap): void {
  type Paint = Parameters<MapLibreMap['setPaintProperty']>
  const set = (id: string, prop: Paint[1], v: Paint[2]) => {
    if (map.getLayer(id)) map.setPaintProperty(id, prop, v)
  }
  for (const l of map.getStyle().layers) {
    const id = l.id
    if (l.type === 'background') set(id, 'background-color', '#0B2347')
    else if (id.startsWith('water') && l.type === 'fill') set(id, 'fill-color', '#06183A')
    else if (id === 'waterway') set(id, 'line-color', '#06183A')
    else if (id === 'building') {
      set(id, 'fill-color', '#133463')
      set(id, 'fill-opacity', 0.7)
    } else if (id.startsWith('landuse') || id.startsWith('landcover') || id === 'park') {
      set(id, 'fill-color', '#0D284F')
      set(id, 'fill-opacity', 0.6)
    } else if (id === 'park_outline') set(id, 'line-opacity', 0)
    else if (l.type === 'line' && id.includes('casing')) set(id, 'line-color', '#1B3F70')
    else if (l.type === 'line' && (id.startsWith('highway') || id.startsWith('tunnel') || id.startsWith('road'))) {
      set(id, 'line-color', '#21497D')
    } else if (l.type === 'line' && id.startsWith('railway')) set(id, 'line-color', '#2A5588')
    else if (l.type === 'symbol') {
      set(id, 'text-color', '#7FA3C2')
      set(id, 'text-halo-color', '#0B2347')
      set(id, 'text-halo-width', 1.4)
    }
  }
}
