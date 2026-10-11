# agents

Strands agents on Amazon Nova (ADR 0004). Specialists run as Lambdas triggered by EventBridge rules. The Commander runs on AgentCore Runtime. **Owner: Vishwa**, including the Verifier's F3 vision prompt.

Every outward action goes through a Cedar check (`cedarpy`), and every decision is emitted as `policy.decided`. Model IDs live in one per-agent config.

## Which tables agents write (#32)

Agents publish contract events, and the projector in `api/` writes `Activity`, `Proposals`, `Alerts`, `Hazards`, `Readings` and `Sos`. Agents never write those. Each remaining table has one agent writer:

| Table | Writer |
|---|---|
| `SegmentRisk` | Sentinel (#9), from what the risk engine returns |
| `Resources` | Dispatcher (#18), on an approved `proposal.decided` |
| `Ledger` | Chronicler (#25) |
| `Reporters` | Verifier (#17) |

**Time sort keys:** write any time used in a key (`Ledger.sim_time`) with `common.keys.utc_key`. That gives fixed-width UTC with a `Z`, so text order is time order. Never use an event's JSON time directly: it drops a zero fraction, so `07:00:00.500000Z` sorts before `07:00:00Z`.
