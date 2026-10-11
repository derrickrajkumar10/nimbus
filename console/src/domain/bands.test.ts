import rules from '@contracts/src/nimbus_contracts/rules.py?raw'
import { BAND_COLOR, BAND_LABEL, LIKELY_FROM, WATCH_FROM, bandForScore } from './bands'

test('score cut-offs match contracts/src/nimbus_contracts/rules.py', () => {
  expect(rules).toContain(`WATCH_FROM = ${WATCH_FROM}`)
  expect(rules).toContain(`LIKELY_FROM = ${LIKELY_FROM}`)
})

test('bandForScore never says flooded', () => {
  expect([bandForScore(92), bandForScore(70), bandForScore(69), bandForScore(40), bandForScore(39)]).toEqual([
    'likely',
    'likely',
    'watch',
    'watch',
    'low',
  ])
})

test('band colours follow the Deep tide rules', () => {
  expect(BAND_COLOR).toEqual({ flooded: '#59D8E6', likely: '#FF7A57', watch: '#F2B34A', low: '#CFE3F0' })
})

test('only observed water is labelled Flooded', () => {
  expect(BAND_LABEL).toEqual({ flooded: 'Flooded', likely: 'Likely', watch: 'Watch', low: 'Low' })
})
