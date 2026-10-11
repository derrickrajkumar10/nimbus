import type { Hazard, HazardClass, HazardOwner, VulnerabilityFlags } from '@contracts/generated/ts/nimbus'

/** The Hazard's no-go radius; the contract defaults it to 30 m. */
export function noGoRadius(h: Hazard): number {
  return h.no_go_radius_m ?? 30
}

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
