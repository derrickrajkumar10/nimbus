import { useEffect, useId, useRef, useState } from 'react'
import type { RainPoint } from '../data/source'
import { rainGeometry } from '../domain/rain'
import { hhmm } from '../domain/time'
import s from './ReplayBar.module.css'

const HEIGHT = 62

/** The storm's hourly rain. The part before the storm clock is filled lighter. */
export function RainChart({ points, clock }: { points: RainPoint[]; clock: string | null }) {
  const box = useRef<HTMLDivElement>(null)
  const clip = useId()
  const [width, setWidth] = useState(600)

  useEffect(() => {
    const el = box.current
    if (!el || typeof ResizeObserver === 'undefined') return
    const ro = new ResizeObserver(([entry]) => setWidth(Math.max(1, entry.contentRect.width)))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const g = rainGeometry(points, clock, width, HEIGHT)
  return (
    <div className={s.chart} ref={box}>
      <svg width={width} height={HEIGHT} viewBox={`0 0 ${width} ${HEIGHT}`} role="img" aria-label="Hourly rain during the storm">
        <defs>
          <clipPath id={clip}>
            <rect x="0" y="0" width={g.nowX ?? 0} height={HEIGHT} />
          </clipPath>
        </defs>
        <path d={g.area} fill="#21497D" opacity=".45" />
        <path d={g.line} fill="none" stroke="#3E78A0" strokeWidth="1.5" />
        <g clipPath={`url(#${clip})`}>
          <path d={g.area} fill="#3E78A0" opacity=".55" />
          <path d={g.line} fill="none" stroke="#A9C6DB" strokeWidth="1.8" />
        </g>
        {g.nowX !== null && g.nowY !== null && clock && (
          <>
            <line x1={g.nowX} x2={g.nowX} y1={2} y2={HEIGHT - 16} stroke="#fff" strokeWidth="1.5" />
            <circle cx={g.nowX} cy={g.nowY} r="4" fill="#fff" />
            <text
              x={g.nowX + (g.nowX > width - 140 ? -8 : 8)}
              y={11}
              textAnchor={g.nowX > width - 140 ? 'end' : 'start'}
              className={s.now}
            >
              {hhmm(clock)} · {g.nowMm} mm/h
            </text>
          </>
        )}
        {g.ticks.map((t) => (
          <text key={t.label} x={t.x} y={HEIGHT - 2} textAnchor={t.anchor} className={s.tick}>
            {t.label}
          </text>
        ))}
      </svg>
    </div>
  )
}
