import { useEffect, useRef } from 'react'

type Bindings = Record<string, (e: KeyboardEvent) => void>

function isTyping(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  return target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)
}

/** Single-key shortcuts. Never fire while typing or with ctrl, meta or alt held. */
export function useShortcuts(bindings: Bindings): void {
  const latest = useRef(bindings)
  useEffect(() => {
    latest.current = bindings
  })

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.ctrlKey || e.metaKey || e.altKey || e.defaultPrevented || isTyping(e.target)) return
      const key = e.key.length === 1 ? e.key.toLowerCase() : e.key
      const handler = latest.current[key]
      if (handler) handler(e)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])
}
