// What the console needs that contracts/fixtures doesn't have yet: the agent
// feed, the Herald's Ward Alert and the storm's rain. Typed with the contract
// shapes so it can move into contracts/fixtures unchanged (see design.md).
import type { Agent, Event, Proposal } from '@contracts/generated/ts/nimbus'
import type { RainPoint } from './source'

const RUN = 'replay-michaung'
const at = (hhmm: string) => `2023-12-04T${hhmm}:00+05:30`
const utc = (iso: string) => new Date(iso).toISOString().replace('.000Z', 'Z')

let seq = 0
function activity(time: string, agent: Agent, saw: string, decided: string, why: string): Event {
  const sim_time = at(time)
  return {
    event_id: `ev-${String(++seq).padStart(4, '0')}`,
    run_id: RUN,
    sim_time,
    emitted_at: utc(sim_time),
    source: agent,
    type: 'agent.activity',
    detail: { agent, saw, decided, why },
  }
}

function policy(time: string, principal: Agent, action: string, resource: string, allowed: boolean, reason: string): Event {
  const sim_time = at(time)
  return {
    event_id: `ev-${String(++seq).padStart(4, '0')}`,
    run_id: RUN,
    sim_time,
    emitted_at: utc(sim_time),
    source: 'cedar',
    type: 'policy.decided',
    detail: { principal, action, resource, allowed, reason },
  }
}

export const SCENE_EVENTS: Event[] = [
  activity(
    '01:45',
    'pathfinder',
    'A knee-deep Reading on Velachery Main Road.',
    'Closed Velachery Main Road to cars and two-wheelers.',
    'Knee-deep water is past the safe depth for both.',
  ),
  activity(
    '01:50',
    'verifier',
    '3 Reports with photos from Velachery Main Road within 10 minutes.',
    'Merged 3 Reports into a knee-deep Reading on Velachery Main Road. Confidence 0.82.',
    "The water reaches a tyre's hub in all three photos.",
  ),
  activity(
    '01:50',
    'verifier',
    'An open manhole in one of the Velachery Main Road photos.',
    'Found an open manhole. Added a 30 m no-go zone and sent it to the corporation.',
    'Manholes belong to the corporation and are invisible under water.',
  ),
  activity(
    '01:55',
    'triage',
    'An SOS from a Ram Nagar side street: 3 people, one elderly.',
    'Ranked the Ram Nagar SOS first. 3 people, one elderly.',
    'Water is rising on that street and an elderly resident is there.',
  ),
  activity(
    '02:00',
    'sentinel',
    '32 mm forecast in the next 3 h after 140 mm in 72 h.',
    'Velachery Main Road north moved to likely: 32 mm forecast in 3 h, ground saturated.',
    'Saturated ground lowers the effective Flood Threshold.',
  ),
  activity(
    '02:00',
    'dispatcher',
    'A flooded Segment with 17 buildings nearby and one free pump.',
    'Proposed Pump 2 for Velachery Main Road. It is the nearest free pump.',
    'Most buildings affected for the shortest travel time.',
  ),
  policy('02:00', 'herald', 'SendAlert', 'proposal:pr-0002', false, "Stopped the Herald's ward-wide alert until an officer approves it."),
  policy('02:00', 'dispatcher', 'ProposeWorkOrder', 'proposal:pr-0001', true, 'Dispatcher may propose Work Orders.'),
]

export const SCENE_WARD_ALERT: Proposal = {
  proposal_id: 'pr-0002',
  run_id: RUN,
  proposed_by: 'herald',
  created_at: at('02:00'),
  rank: 2,
  reason: 'The Herald drafted this for the whole ward. Ward-wide alerts wait for an officer.',
  action: {
    kind: 'ward_alert',
    message_en: 'Velachery Main Road is flooded knee-deep. Use 100 Feet Road.',
    message_ta: 'வேளச்சேரி மெயின் ரோட்டில் முழங்கால் அளவு தண்ணீர். 100 அடி சாலையைப் பயன்படுத்தவும்.',
    recipient_count: 1240,
  },
  status: 'pending',
  decided_by: null,
  decided_at: null,
}

// Open-Meteo hourly precipitation (mm), lat 12.975 lon 80.219, 3 Dec 2023 18:00 to 4 Dec 12:00 IST.
const RAIN_MM = [2.3, 1.4, 2.2, 1.6, 1.8, 1.9, 2.9, 2.5, 3.2, 2.8, 1.2, 3.4, 6.5, 11.5, 14.5, 14.4, 12.1, 9.4, 8.9]
const RAIN_START_MS = Date.parse('2023-12-03T18:00:00+05:30')

function istIso(ms: number): string {
  return new Date(ms + 5.5 * 3600000).toISOString().slice(0, 19) + '+05:30'
}

export const MICHAUNG_RAIN: RainPoint[] = RAIN_MM.map((mm, i) => ({ time: istIso(RAIN_START_MS + i * 3600000), mm }))
