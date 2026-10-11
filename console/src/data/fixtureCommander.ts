// Stands in for the AgentCore Commander (#29) until its streaming endpoint exists.
import { buildCommanderAnswer, type Snapshot } from '../domain/commander'
import type { CommanderClient } from './source'

let getSnapshot: (() => Snapshot) | null = null

/** The console registers a getter over its latest data; ask() reads it. */
export function registerSnapshot(fn: () => Snapshot): void {
  getSnapshot = fn
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))

export function createFixtureCommander(opts: { delayMs?: number } = {}): CommanderClient {
  const delayMs = opts.delayMs ?? 35
  return {
    async *ask(question) {
      if (!getSnapshot) throw new Error('No console data registered for the Commander')
      const answer = buildCommanderAnswer(question, getSnapshot())
      // Each chunk is a word with its trailing whitespace, so chunks join back exactly.
      for (const chunk of answer.split(/(?<=\s)/)) {
        if (delayMs) await sleep(delayMs)
        yield chunk
      }
    },
  }
}
