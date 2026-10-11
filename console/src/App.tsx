import { useCallback, useState } from 'react'
import s from './App.module.css'
import type { FeedItem } from './domain/activity'
import { ActivityPanel } from './ui/ActivityPanel'
import { AskCommander } from './ui/AskCommander'
import { DecisionsPanel } from './ui/DecisionsPanel'
import { MapView } from './ui/map/MapView'
import { ResourcesSection } from './ui/ResourcesSection'
import { SosSection } from './ui/SosSection'
import { TopBar } from './ui/TopBar'

export default function App() {
  const [asked, setAsked] = useState<FeedItem[]>([])
  const upsert = useCallback(
    (item: FeedItem) =>
      setAsked((list) => {
        const i = list.findIndex((x) => x.id === item.id)
        return i === -1 ? [...list, item] : list.map((x, j) => (j === i ? item : x))
      }),
    [],
  )

  return (
    <div className={s.app}>
      <TopBar />
      <aside className={`${s.panel} ${s.left}`} aria-label="Decisions">
        <div className={s.scroll}>
          <DecisionsPanel />
          <SosSection />
          <ResourcesSection />
        </div>
      </aside>
      <main className={s.stage} aria-label="Map">
        <MapView />
      </main>
      <aside className={`${s.panel} ${s.right}`} aria-label="Activity">
        <ActivityPanel extra={asked} footer={<AskCommander onItem={upsert} />} />
      </aside>
    </div>
  )
}
