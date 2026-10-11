import type { HazardClass, HazardOwner, VulnerabilityFlags } from '@contracts/generated/ts/nimbus'

export function sosFlagsText(f: VulnerabilityFlags): string {
  const words: string[] = []
  if (f.elderly) words.push('Elderly resident')
  if (f.child) words.push('Child')
  if (f.medical) words.push('Medical need')
  return words.join(' · ')
}

export const HAZARD_LABEL: Record<HazardClass, string> = {
  open_manhole: 'Open manhole',
  live_wire: 'Live wire',
  fallen_tree: 'Fallen tree',
  stranded_vehicle: 'Stranded vehicle',
}

export const OWNER_LABEL: Record<HazardOwner, string> = {
  corporation: 'Corporation',
  power_utility: 'Power utility',
}
