import { hazards } from '../test/fixtures'
import { HAZARD_LABEL, OWNER_LABEL, noGoRadius, sosFlagsText } from './sos'

test('noGoRadius uses the contract default of 30 m when omitted', () => {
  expect(noGoRadius({ ...hazards[0], no_go_radius_m: 45 })).toBe(45)
  const { no_go_radius_m: _, ...without } = hazards[0]
  expect(noGoRadius(without)).toBe(30)
})

test('sosFlagsText names each flag in words', () => {
  expect(sosFlagsText({ elderly: true, child: false, medical: true })).toBe('Elderly resident · Medical need')
  expect(sosFlagsText({ elderly: false, child: true, medical: false })).toBe('Child')
  expect(sosFlagsText({ elderly: false, child: false, medical: false })).toBe('')
})

test('hazard and owner labels', () => {
  expect(HAZARD_LABEL.open_manhole).toBe('Open manhole')
  expect(HAZARD_LABEL.live_wire).toBe('Live wire')
  expect(OWNER_LABEL.corporation).toBe('Corporation')
  expect(OWNER_LABEL.power_utility).toBe('Power utility')
})
