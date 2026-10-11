import type { RiskBand } from '@contracts/generated/ts/nimbus'

// Predicted risk is warm; only a Reading's observed water is cyan.
export const BAND_COLOR: Record<RiskBand, string> = {
  flooded: '#59D8E6',
  likely: '#FF7A57',
  watch: '#F2B34A',
  low: '#CFE3F0',
}

export const BAND_LABEL: Record<RiskBand, string> = {
  flooded: 'Flooded',
  likely: 'Likely',
  watch: 'Watch',
  low: 'Low',
}
