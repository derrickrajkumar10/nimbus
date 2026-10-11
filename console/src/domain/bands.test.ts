import { BAND_COLOR, BAND_LABEL } from './bands'

test('band colours follow the Deep tide rules', () => {
  expect(BAND_COLOR).toEqual({ flooded: '#59D8E6', likely: '#FF7A57', watch: '#F2B34A', low: '#CFE3F0' })
})

test('only observed water is labelled Flooded', () => {
  expect(BAND_LABEL).toEqual({ flooded: 'Flooded', likely: 'Likely', watch: 'Watch', low: 'Low' })
})
