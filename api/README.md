# api

HTTP API: API Gateway HTTP API plus Python Lambdas, typed with `nimbus_contracts`. **Owner: Varun.** Citizen routes serve the Flutter app. Console routes serve the ward console. Document every route here with its request and response contract types, so Derrick can build against it.

## Event persistence (plan)

Agents and engines publish events to the bus. The console and app read DynamoDB. Nothing in the repo copied events into the tables, so `GET /activity`, `GET /proposals` and the rest would read empty tables. This is the plan for closing that gap. It is a plan, not built yet.

### Rule: one writer per table

A table is written either by the **projector** (below), or by the **lane that owns the data**, never both.

| Table | Written by | From |
|---|---|---|
| `Activity` | projector | `agent.activity`, `policy.decided` |
| `Proposals` | projector creates; API route updates | `proposal.created`; `POST /proposals/{id}/decision` |
| `Alerts` | projector | `alert.sent` |
| `Hazards` | projector | `hazard.detected` |
| `Readings` | projector | `report.verified` |
| `Sos` | projector (`sos.created`), then fills the ranked fields from `sos.ranked` | events |
| `Reports` | API (`POST /reports`) | request, then it emits `report.created` |
| `SegmentRisk` | **risk engine (Goutam)** | not derivable from `risk.changed` (see below) |
| `Runs` | **Replay Driver (Goutam)** and `POST /runs` | `clock.tick` is not projected |
| `Resources`, `Reporters`, `Ledger`, `PlaceIndex` | owning lane, or open (see below) | |
| `Devices`, `SavedPlaces` | API | requests |
| `Segments` | F1 (Goutam) | offline job |

### The projector

- One Lambda, `api/projector/`, triggered by one EventBridge rule on the `nimbus` bus matching `source` prefix `nimbus.`. Defined in `NimbusApi` (`infra/stacks/api.py`), with a dead-letter queue.
- Parses `detail` with `nimbus_contracts.events.Event`, so a malformed event is rejected before anything is written. Table names come from the `/nimbus/tables/*` SSM parameters.
- Every key leads with the event's `run_id` (ADR 0001). A Replay's events can't land in `live`.
- Idempotent, because EventBridge delivers at least once: puts use deterministic keys, and `proposal.created` uses `attribute_not_exists` so a redelivery can't overwrite a Proposal an officer has already decided.
- `Activity`'s sort key is `emitted_at` in UTC with a `Z` suffix, then `#event_id`, so the feed sorts in time order (`contracts/storage.md`).
- Floats are stored as `Decimal` (boto3's DynamoDB resource rejects `float`).

### Proposal decisions

`POST /proposals/{id}/decision` updates the row itself with a conditional write (`status = pending`), then emits `proposal.decided`. That makes a double approval fail cleanly, and the console sees the new status on its next 2 s poll without waiting for the projector.

### Gaps this plan found

1. **`risk.changed` can't produce a `SegmentRisk` row.** It carries `segment_id`, `previous_band`, `band`, `score`, `minutes_to_flood` and `reasons`, but not `flood_threshold_mm`, and it fires only when a Segment crosses a band, while the table holds the latest score. So the risk engine must write `SegmentRisk` itself.
2. **`Runs` has no named writer** for run status, speed and current `sim_time`. Proposed: the Replay Driver, with `POST /runs` only asking it to start or pause.
3. **`Ledger`, `Reporters`, `Resources` and `PlaceIndex` have no event that obviously feeds them.** Who writes a Resource's status change after a Work Order is approved? Who writes `Ledger` entries? Not decided here.
4. **`GET /hit-rate` and `GET /after-action`** serve "stored results", but `storage.md` has no table or S3 key for them.

### Not decided here

Whether `sim_time` on `Runs` is advanced by the projector on `clock.tick` (rejected for now: two writers).
