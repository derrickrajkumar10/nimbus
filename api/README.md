# api

HTTP API: API Gateway HTTP API plus Python Lambdas, typed with `nimbus_contracts`. **Owner: Varun.** Citizen routes serve the Flutter app. Console routes serve the ward console. Document every route here with its request and response contract types, so Derrick can build against it.

## Event persistence (plan)

Agents and engines publish events to the bus. The console and app read DynamoDB. Nothing in the repo copied events into the tables, so `GET /activity`, `GET /proposals` and the rest would read empty tables. This is the plan for closing that gap. It is a plan, not built yet.

### Rule: one writer per table

A table is written either by the **projector** (below), or by the **lane that owns the data**, never both. Agents only publish contract events through `EventBridgeBus`; they don't write the projector's tables.

| Table | Written by | From |
|---|---|---|
| `Activity` | projector | `agent.activity`, `policy.decided` |
| `Proposals` | projector creates; API route updates | `proposal.created`; `POST /proposals/{id}/decision` |
| `Alerts` | projector | `alert.sent` |
| `Hazards` | projector | `hazard.detected` |
| `Readings` | projector | `report.verified` |
| `Sos` | projector (`sos.created`), then fills the ranked fields from `sos.ranked` | events |
| `Reports` | API (`POST /reports`) | request, then it emits `report.created` |
| `SegmentRisk` | **Sentinel** (#9), the single writer; the risk engine is a pure function and doesn't write it | `score_segments` output |
| `Runs` | **Replay Driver** (#14) creates and updates; `POST /runs` only asks it to start or pause | `clock.tick` is not projected |
| `Resources` | **Dispatcher** (#18) sets `en_route` on an approved `proposal.decided`; initial rows seeded per Run by the Replay Driver (proposed) | no event carries a Resource status change |
| `Ledger` | **Chronicler** (#25) | |
| `Reporters` | **Verifier** (#17) | |
| `PlaceIndex` | **API**, on `PUT /saved-places` (#7); a Replay's demo devices are indexed when they subscribe to the Run (owner open, see below) | |
| `Devices`, `SavedPlaces` | API | requests |
| `Segments` | F1 (Goutam, #13) | offline job |

### The projector

- One Lambda, `api/projector/`, triggered by one EventBridge rule on the `nimbus` bus matching `source` prefix `nimbus.`. Defined in `NimbusApi` (`infra/stacks/api.py`), with a dead-letter queue.
- Parses `detail` with `nimbus_contracts.events.Event`, so a malformed event is rejected before anything is written. Table names come from the `/nimbus/tables/*` SSM parameters.
- Every key leads with the event's `run_id` (ADR 0001). A Replay's events can't land in `live`.
- Idempotent, because EventBridge delivers at least once: puts use deterministic keys, and `proposal.created` uses `attribute_not_exists` so a redelivery can't overwrite a Proposal an officer has already decided.
- `Activity`'s sort key is built from `emitted_at` parsed and re-formatted as `%Y-%m-%dT%H:%M:%S.%fZ` (UTC, fixed width), then `#event_id`. Never use the event's JSON string: it drops a zero fraction, so `07:00:00Z` would sort after `07:00:00.500000Z`. `agents/common/keys.py` (`utc_key`, on `vishwa/32-utc-sort-keys`) does the same for agents.
- Floats are stored as `Decimal` (boto3's DynamoDB resource rejects `float`).

### Proposal decisions

`POST /proposals/{id}/decision` updates the row itself with a conditional write (`status = pending`), then emits `proposal.decided`. That makes a double approval fail cleanly, and the console sees the new status on its next 2 s poll without waiting for the projector.

### Settled by the issues

- `risk.changed` can't produce a `SegmentRisk` row (it has no `flood_threshold_mm` and fires only on band crossings), so the Sentinel writes the row with what the risk engine returns. Flood Threshold nudges are applied by the risk engine from `Readings` when it scores, and land in `SegmentRisk.flood_threshold_mm`.
- Agents' events carry `emitted_at` in UTC with a `Z` suffix and `source` set to the agent name. `EventBridgeBus` sends `Source = nimbus.<source>`, `DetailType = type` and `Detail` = the whole event.

### Still open

1. **`GET /after-action` and `GET /hit-rate`:** #25 and #26 both say "store the result". Proposed: one JSON object each in the `data` bucket, `results/{run_id}/after-action.json` and `results/{run_id}/hit-rate.json`, written by the Chronicler and by Goutam's Hit Rate job.
2. **`POST /runs`:** how it starts and pauses the Replay Driver (#14 suggests Step Functions). The API needs the state machine ARN from SSM and an input shape.
3. **Herald to FCM sender (#6, #10):** proposed a synchronous Lambda invoke of the function named at `/nimbus/lambdas/send-push`, with `{run_id, device_ids, title: {en, ta}, body: {en, ta}, data}`; the sender picks the text by `Devices.language`.
4. **Replay `PlaceIndex`:** who indexes the demo phones' Saved Places under a Replay Run (#14)? Proposed: the Replay Driver, using the API's `PlaceIndex` write helper.
5. **`POST /routes` to the Pathfinder (#23):** no route request/response type exists in `contracts/`, and the Pathfinder's function name isn't published.
6. **`Ledger` sort key:** the Chronicler must write `sim_time` in UTC with `Z`; fixtures use IST (`+05:30`), which would not sort in time order.

### Not decided here

Whether `sim_time` on `Runs` is advanced by the projector on `clock.tick` (rejected for now: two writers).
