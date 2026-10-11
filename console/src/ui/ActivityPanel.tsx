import { useRef, useState, type ReactNode } from 'react'
import { useConfig, useConsoleData } from '../data/queries'
import { AGENT_LABEL, filterFeed, toFeedItems, type FeedFilter, type FeedItem } from '../domain/activity'
import { splitProposals } from '../domain/proposals'
import { FeedRow } from './FeedRow'
import { Chevron } from './icons'
import s from './ActivityPanel.module.css'

const filterLabel = (f: FeedFilter) => (f === 'all' ? 'All agents' : f === 'cedar' ? 'Cedar' : AGENT_LABEL[f])

export function ActivityPanel(props: { extra?: FeedItem[]; footer?: ReactNode }) {
  const data = useConsoleData()
  const cfg = useConfig()
  const [filter, setFilter] = useState<FeedFilter>('all')
  const [menu, setMenu] = useState(false)
  const [expanded, setExpanded] = useState<string | null>(null)
  // Feed length when the officer scrolled away from the top; rows above it are "new".
  const [anchor, setAnchor] = useState<number | null>(null)
  const scroller = useRef<HTMLDivElement>(null)

  const ctx = { resources: data.resources, segments: data.segments, readings: data.readings, ...cfg }
  const feed = toFeedItems(data.events, splitProposals(data.proposals).decided, ctx)
  const items = filterFeed([...(props.extra ?? [])].reverse().concat(feed), filter)
  const agents = [...new Set(feed.flatMap((i) => (i.kind === 'agent' ? [i.agent] : [])))]
  const fresh = anchor === null ? 0 : Math.max(0, items.length - anchor)

  const onScroll = () => {
    const top = scroller.current?.scrollTop ?? 0
    if (top > 0 && anchor === null) setAnchor(items.length)
    if (top === 0 && anchor !== null) setAnchor(null)
  }

  const choose = (f: FeedFilter) => {
    setFilter(f)
    setMenu(false)
  }

  return (
    <>
      <div className={s.head}>
        <h2 className={s.title}>Activity</h2>
        <div className={s.filterWrap}>
          <button className={s.filter} aria-haspopup="listbox" aria-expanded={menu} onClick={() => setMenu((m) => !m)}>
            {filterLabel(filter)} <Chevron />
          </button>
          {menu && (
            <ul className={s.menu} role="listbox" aria-label="Filter activity">
              {(['all', 'cedar', ...agents] as FeedFilter[]).map((f) => (
                <li key={f} role="option" aria-selected={f === filter} onClick={() => choose(f)}>
                  {filterLabel(f)}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
      <div className={s.scroll} ref={scroller} onScroll={onScroll}>
        {fresh > 0 && (
          <button
            className={s.pill}
            onClick={() => {
              scroller.current?.scrollTo({ top: 0, behavior: 'smooth' })
              setAnchor(null)
            }}
          >
            {fresh} new
          </button>
        )}
        <ul className={s.list}>
          {items.map((item) => (
            <FeedRow
              key={item.id}
              item={item}
              expanded={expanded === item.id}
              onToggle={() => setExpanded((e) => (e === item.id ? null : item.id))}
            />
          ))}
        </ul>
        {!data.isLoading && items.length === 0 && <p className={s.empty}>No activity in this Run yet.</p>}
      </div>
      {props.footer}
    </>
  )
}
