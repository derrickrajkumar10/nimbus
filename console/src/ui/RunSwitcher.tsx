import { useEffect, useRef, useState } from 'react'
import { useConfig, useSource } from '../data/queries'
import { runName, runTag } from '../domain/runs'
import { Chevron } from './icons'
import s from './RunSwitcher.module.css'

export function RunSwitcher() {
  const { runId } = useConfig()
  const source = useSource()
  const [open, setOpen] = useState(false)
  const root = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent ? e.key === 'Escape' : !root.current?.contains(e.target as Node)) setOpen(false)
    }
    window.addEventListener('mousedown', close)
    window.addEventListener('keydown', close)
    return () => {
      window.removeEventListener('mousedown', close)
      window.removeEventListener('keydown', close)
    }
  }, [open])

  const choose = (id: string) => {
    setOpen(false)
    if (id === runId) return
    const url = new URL(window.location.href)
    url.searchParams.set('run', id)
    window.location.assign(url.toString())
  }

  const tag = runTag(runId)
  return (
    <div className={s.root} ref={root}>
      <button
        className={s.button}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={`Run: ${tag} ${runName(runId)}`}
        onClick={() => setOpen((o) => !o)}
      >
        <span className={tag === 'Replay' ? s.tagReplay : s.tagLive}>{tag}</span>
        <b className={s.name}>{runName(runId)}</b>
        <Chevron color="var(--muted)" />
      </button>
      {open && (
        <ul className={s.menu} role="listbox" aria-label="Runs">
          {source.runs().map((id) => (
            <li key={id} role="option" aria-selected={id === runId} className={s.option} onClick={() => choose(id)}>
              <span className={runTag(id) === 'Replay' ? s.tagReplay : s.tagLive}>{runTag(id)}</span>
              {runName(id)}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
