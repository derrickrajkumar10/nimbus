import s from './App.module.css'
import { TopBar } from './ui/TopBar'

export default function App() {
  return (
    <div className={s.app}>
      <TopBar />
      <aside className={`${s.panel} ${s.left}`} aria-label="Decisions" />
      <main className={s.stage} aria-label="Map" />
      <aside className={`${s.panel} ${s.right}`} aria-label="Activity" />
    </div>
  )
}
