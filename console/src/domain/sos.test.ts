import { HAZARD_LABEL, OWNER_LABEL, sosFlagsText } from './sos'

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
