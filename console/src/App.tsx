import s from './App.module.css'
import { DecisionsPanel } from './ui/DecisionsPanel'
import { TopBar } from './ui/TopBar'

export default function App() {
  return (
    <div className={s.app}>
      <TopBar />
      <aside className={`${s.panel} ${s.left}`} aria-label="Decisions">
        <div className={s.scroll}>
          <DecisionsPanel />
        </div>
      </aside>
      <main className={s.stage} aria-label="Map" />
      <aside className={`${s.panel} ${s.right}`} aria-label="Activity" />
    </div>
  )
}
