import { AGENT_LABEL, type FeedItem } from '../domain/activity'
import { hhmm } from '../domain/time'
import s from './ActivityPanel.module.css'

export function FeedRow(props: { item: FeedItem; expanded: boolean; onToggle(): void }) {
  const { item } = props
  const time = item.time ? hhmm(item.time) : ''

  if (item.kind === 'commander') {
    return (
      <li className={s.commander}>
        <div className={s.who}>Commander</div>
        <p className={s.question}>{item.question}</p>
        <p className={s.answer} aria-live="polite" aria-busy={item.streaming}>
          {item.answer}
          {item.streaming && <span className={s.caret} aria-hidden="true" />}
        </p>
      </li>
    )
  }

  if (item.kind === 'agent') {
    return (
      <li className={s.ev}>
        <span className={`${s.t} num`}>{time}</span>
        <button className={s.body} aria-expanded={props.expanded} onClick={props.onToggle}>
          <span className={s.who}>{AGENT_LABEL[item.agent]}</span>
          <span className={s.what}>{item.decided}</span>
          {props.expanded && (
            <span className={s.more}>
              <span>Saw: {item.saw}</span>
              <span>Why: {item.why}</span>
            </span>
          )}
        </button>
      </li>
    )
  }

  return (
    <li className={s.ev}>
      <span className={`${s.t} num`}>{time}</span>
      <div className={s.body}>
        {item.kind === 'cedar' ? (
          <>
            <span className={s.who}>
              Cedar <span className={s.held}>Held</span>
            </span>
            <span className={s.what}>{item.reason}</span>
          </>
        ) : (
          <>
            <span className={`${s.who} ${s.officer}`}>{item.who}</span>
            <span className={s.what}>{item.text}</span>
          </>
        )}
      </div>
    </li>
  )
}
