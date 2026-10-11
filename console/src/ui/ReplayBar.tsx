import { useState } from 'react'
import { useConfig, useConsoleData, useSource } from '../data/queries'
import type { ReplayState } from '../data/source'
import { nextSpeed } from '../domain/rain'
import { useShortcuts } from '../state/shortcuts'
import { Pause, Play } from './icons'
import { RainChart } from './RainChart'
import s from './ReplayBar.module.css'

export function ReplayBar() {
  const source = useSource()
  const { runId } = useConfig()
  const { rain, clock } = useConsoleData()
  const [state, setState] = useState<ReplayState>(() => source.replay.get(runId))

  const update = (next: ReplayState) => source.replay.set(runId, next).then(setState)
  const toggle = () => update({ ...state, playing: !state.playing })

  useShortcuts({
    ' ': (e) => {
      // A focused button already handles Space itself.
      if ((e.target as HTMLElement | null)?.tagName === 'BUTTON') return
      e.preventDefault()
      void toggle()
    },
  })

  return (
    <div className={s.replay}>
      <div className={s.ctl}>
        <button className={s.play} aria-label={state.playing ? 'Pause Replay' : 'Play Replay'} onClick={toggle}>
          {state.playing ? <Pause /> : <Play />}
        </button>
        <button
          className={`${s.speed} num`}
          aria-label={`Replay speed ${state.speed}×`}
          onClick={() => update({ ...state, speed: nextSpeed(state.speed) })}
        >
          {state.speed}×
        </button>
      </div>
      <RainChart points={rain} clock={clock} />
    </div>
  )
}
