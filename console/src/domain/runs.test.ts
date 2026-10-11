import { isReplay, runName, runTag } from './runs'

test('Run names and tags', () => {
  expect(runName('replay-michaung')).toBe('Cyclone Michaung')
  expect(runName('replay-vardah-2016')).toBe('Vardah 2016')
  expect(runName('live')).toBe('Live storm')
  expect(runTag('replay-michaung')).toBe('Replay')
  expect(runTag('live')).toBe('Live')
  expect(isReplay('live')).toBe(false)
})
