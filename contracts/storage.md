# DynamoDB tables

Every mutable table puts `run_id` first in its partition key ([ADR 0001](../docs/adr/0001-runs-isolate-replay-state.md)). A query that forgets the Run can't see the wrong storm. IDs are ULIDs with a short prefix (`rp-`, `rd-`, `hz-`, `sos-`, `pr-`, `al-`), so sorting by SK gives creation order.

| Table | PK | SK | Holds | Main reads |
|---|---|---|---|---|
| `Segments` | `segment_id` | | `Segment` (static, from F1) | Load all by Scan once per cold start |
| `SegmentRisk` | `run_id` | `segment_id` | `SegmentRisk`, latest only | Console map, Pathfinder, Herald |
| `Reports` | `run_id` | `report_id` | `Report` | Verifier (merge window) |
| `Readings` | `run_id` | `reading_id` | `Reading` | Risk engine, map, ledger |
| `Hazards` | `run_id` | `hazard_id` | `Hazard` | Map, Pathfinder |
| `Sos` | `run_id` | `sos_id` | `Sos` + latest `RankedSos` fields | Triage, console (officers only) |
| `Resources` | `run_id` | `resource_id` | `Resource` | Dispatcher, console |
| `Proposals` | `run_id` | `proposal_id` | `Proposal` | Console queue (filter `status = pending`) |
| `Alerts` | `run_id` | `alert_id` | `Alert` | Console, after-action report |
| `Activity` | `run_id` | `emitted_at#event_id` | `agent.activity` and `policy.decided` events | Console activity feed |
| `Ledger` | `run_id#segment_id` | `sim_time` | Per-Segment flood history entries | Chronicler |
| `Reporters` | `run_id` | `reporter_id` | Trust Score per Reporter, per Run | Verifier |
| `Runs` | `run_id` | | Run status, storm, speed, current `sim_time` | Replay Driver, console |
| `Devices` | `device_id` | | FCM token, language (`en`/`ta`) | Herald |
| `SavedPlaces` | `device_id` | `place_id` | `SavedPlace` | App |
| `PlaceIndex` | `run_id#segment_id` | `device_id#place_id` | Who to alert when a Segment changes | Herald |

Key attributes are strings. A composite key such as `run_id#segment_id` is one attribute with that literal name, holding values like `live#27320162-0`. Sort keys that hold a time (`Ledger.sim_time`, the `emitted_at` in `Activity`) sort as text, so write them in UTC with a `Z` suffix, never with an offset like `+05:30`.

`PlaceIndex` is written per Run. Live Saved Places index under `live`. A Replay indexes only the demo devices that subscribed to it, so live users never get Replay alerts.

Photos live in S3 at `reports/{run_id}/{report_id}.jpg`. F1 output lives at `segments/v{n}/segments.geojson` and is never overwritten.
