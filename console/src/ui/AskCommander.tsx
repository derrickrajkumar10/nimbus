import { useEffect, useId, useRef, useState, type FormEvent } from 'react'
import { registerSnapshot } from '../data/fixtureCommander'
import { useConfig, useConsoleData, useSource } from '../data/queries'
import type { FeedItem } from '../domain/activity'
import { useShortcuts } from '../state/shortcuts'
import s from './AskCommander.module.css'

type CommanderItem = Extract<FeedItem, { kind: 'commander' }>

export function AskCommander({ onItem }: { onItem(item: CommanderItem): void }) {
  const source = useSource()
  const { runId, wardName } = useConfig()
  const data = useConsoleData()
  const id = useId()
  const input = useRef<HTMLInputElement>(null)
  const latest = useRef(data)
  const asked = useRef(0)
  const [question, setQuestion] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    latest.current = data
  })
  useEffect(() => {
    registerSnapshot(() => ({ ...latest.current, wardName }))
  }, [wardName])

  useShortcuts({
    '/': (e) => {
      e.preventDefault()
      input.current?.focus()
    },
  })

  async function submit(e: FormEvent) {
    e.preventDefault()
    const q = question.trim()
    if (!q || busy) return
    setBusy(true)
    const item: CommanderItem = { kind: 'commander', id: `ask-${++asked.current}`, time: data.clock, question: q, answer: '', streaming: true }
    onItem(item)
    let answer = ''
    try {
      for await (const chunk of source.commander.ask(q, runId)) {
        answer += chunk
        onItem({ ...item, answer })
      }
    } catch {
      answer ||= "The Commander couldn't answer. Try again."
    }
    onItem({ ...item, answer, streaming: false })
    setQuestion('')
    setBusy(false)
    requestAnimationFrame(() => input.current?.focus())
  }

  return (
    <form className={s.ask} onSubmit={submit}>
      <label className={s.label} htmlFor={id}>
        Ask the Commander
      </label>
      <div className={s.field}>
        <input
          id={id}
          ref={input}
          value={question}
          disabled={busy}
          autoComplete="off"
          placeholder="What changed in the last hour?"
          onChange={(e) => setQuestion(e.target.value)}
        />
        <kbd aria-hidden="true">/</kbd>
      </div>
    </form>
  )
}
