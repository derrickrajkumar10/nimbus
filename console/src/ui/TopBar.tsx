import { useConfig, useConsoleData, useSyncStatus } from '../data/queries'
import { formatClock } from '../domain/time'
import { WaveMark } from './icons'
import { RunSwitcher } from './RunSwitcher'
import s from './TopBar.module.css'

export function TopBar() {
  const { wardName, officerName } = useConfig()
  const { clock } = useConsoleData()
  const { secondsAgo, reconnecting } = useSyncStatus()
  const c = clock ? formatClock(clock) : null

  return (
    <header className={s.top}>
      <div className={s.brand}>
        <span className={s.mark}>
          <WaveMark />
          NIMBUS
        </span>
        <span className={s.divider} />
        <span className={s.ward}>{wardName} ward</span>
      </div>
      <div className={s.center}>
        <RunSwitcher />
        <span className={`${s.clock} num`} aria-label="Storm time">
          {c ? (
            <>
              {c.time}
              <span className={s.date}>{c.date}</span>
            </>
          ) : (
            '—'
          )}
        </span>
      </div>
      <div className={s.user}>
        <span className={s.sync} role="status">
          <i className={reconnecting ? s.dotWarn : s.dot} />
          {reconnecting ? 'Reconnecting…' : secondsAgo === null ? 'Connecting…' : `Updated ${secondsAgo} s ago`}
        </span>
        <span>{officerName}</span>
      </div>
    </header>
  )
}
