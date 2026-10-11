import type { RiskBand } from '@contracts/generated/ts/nimbus'

// Predicted risk is warm; only a Reading's observed water is cyan.
export const BAND_COLOR: Record<RiskBand, string> = {
  flooded: '#59D8E6',
  likely: '#FF7A57',
  watch: '#F2B34A',
  low: '#CFE3F0',
}

// Risk Score cut-offs from contracts/src/nimbus_contracts/rules.py (Python only; a test guards drift).
export const WATCH_FROM = 40
export const LIKELY_FROM = 70

/** The predicted band for a score. Never "flooded": only a Reading makes that. */
export function bandForScore(score: number): Exclude<RiskBand, 'flooded'> {
  if (score >= LIKELY_FROM) return 'likely'
  if (score >= WATCH_FROM) return 'watch'
  return 'low'
}

export const BAND_LABEL: Record<RiskBand, string> = {
  flooded: 'Flooded',
  likely: 'Likely',
  watch: 'Watch',
  low: 'Low',
}
