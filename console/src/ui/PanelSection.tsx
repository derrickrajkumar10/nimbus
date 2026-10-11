import { useId, type ReactNode } from 'react'
import s from './PanelSection.module.css'

export function PanelSection(props: {
  title: string
  count?: number
  countTone?: 'teal' | 'sos'
  hint?: string
  children: ReactNode
}) {
  const id = useId()
  return (
    <section className={s.section} aria-labelledby={id}>
      <div className={s.head}>
        <h2 id={id} className={s.title}>
          {props.title}
          {props.count !== undefined && (
            <span className={`${s.count} ${props.countTone === 'sos' ? s.sos : ''} num`}>{props.count}</span>
          )}
        </h2>
        {props.hint && <span className={`${s.hint} num`}>{props.hint}</span>}
      </div>
      {props.children}
    </section>
  )
}
