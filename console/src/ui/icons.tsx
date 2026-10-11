// The console's only icons. Inline strokes, no icon library.
type IconProps = { size?: number; color?: string }

export function WaveMark({ size = 22 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 22 22" fill="none" aria-hidden="true">
      <path d="M2 13c2.2 0 2.2-2 4.5-2s2.3 2 4.5 2 2.2-2 4.5-2 2.3 2 4.5 2" stroke="#4FD1D9" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M2 17.5c2.2 0 2.2-2 4.5-2s2.3 2 4.5 2 2.2-2 4.5-2 2.3 2 4.5 2" stroke="#4FD1D9" strokeOpacity=".5" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M6.5 8.5a4.5 4.5 0 0 1 9 0" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  )
}

export function Chevron({ size = 10, color = 'currentColor' }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 10 10" aria-hidden="true">
      <path d="M2 3.5l3 3 3-3" stroke={color} strokeWidth="1.4" fill="none" strokeLinecap="round" />
    </svg>
  )
}

export function Pump({ size = 14, color = 'currentColor' }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <path d="M7 2c2 2.6 3.5 4.4 3.5 6.2A3.5 3.5 0 0 1 3.5 8.2C3.5 6.4 5 4.6 7 2z" stroke={color} strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  )
}

export function Crew({ size = 14, color = 'currentColor' }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <path d="M7 1.8l4 5.2H8.6l2.4 3.4H3l2.4-3.4H3z" stroke={color} strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M7 10.4v2" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  )
}

export function HazardMark({ size = 13, color = 'currentColor' }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" aria-hidden="true">
      <rect x="6.1" y="2.5" width="1.8" height="6" rx=".9" fill={color} />
      <circle cx="7" cy="11" r="1.1" fill={color} />
    </svg>
  )
}

export function Play({ size = 14, color = '#fff' }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 16" aria-hidden="true">
      <path d="M2 1.5v13L13 8z" fill={color} />
    </svg>
  )
}

export function Pause({ size = 14, color = '#fff' }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" aria-hidden="true">
      <rect x="2.5" y="1.5" width="3" height="11" rx="1" fill={color} />
      <rect x="8.5" y="1.5" width="3" height="11" rx="1" fill={color} />
    </svg>
  )
}

export function Check({ size = 14, color = 'currentColor' }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <path d="M2.5 7.5l3 3 6-7" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
