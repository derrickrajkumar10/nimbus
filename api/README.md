# api

HTTP API: API Gateway HTTP API plus Python Lambdas, typed with `nimbus_contracts`. **Owner: Varun.** Citizen routes serve the Flutter app. Console routes serve the ward console. Document every route here with its request and response contract types, so Derrick can build against it.

## Console API (#8)

`api/console/`, one Lambda behind an API Gateway HTTP API (`nimbus-console`, stack `NimbusApi`). The base URL is the stack output `ConsoleApiUrl` and the SSM parameter `/nimbus/api/console-url`. **There is no login yet** (issue #19), so treat it as open. It is throttled to 25 requests per second per route (burst 50), so a runaway client can't run up the bill. A console polling `/activity` every 2 s uses 0.5.

Every route needs `run_id` (`live` or `replay-<name>`). A request can't see another Run's rows (ADR 0001). Errors are `{"error": "<code>", "message": "..."}`.

| Route | Returns | Contract type |
|---|---|---|
| `GET /risk?run_id=` | latest risk per Segment | `SegmentRisk[]` |
| `GET /readings?run_id=` | verified Readings | `Reading[]` |
| `GET /hazards?run_id=` | Hazards | `Hazard[]` |
| `GET /resources?run_id=` | Resources | `Resource[]` |
| `GET /sos?run_id=` | SOS calls, ranked ones first | `Sos` plus `rank`, `danger_score`, `reasons`, `merged_sos_ids` once Triage has ranked it. Officers only once #19 lands |
| `GET /proposals?run_id=&status=pending` | Proposals by `rank`; `status` is optional (`pending`, `approved`, `edited`, `rejected`) | `Proposal[]` |
| `GET /activity?run_id=&since=&limit=` | agent feed, oldest first | `{items: Event[], cursor: string \| null}` |
| `POST /proposals/{proposal_id}/decision` | the decided Proposal | body `DecisionRequest`, response `Proposal` |

**Polling the feed.** Call `/activity` with no `since`, then pass the returned `cursor` as `since` on each poll (every 2 s). The cursor is opaque and exclusive, so nothing repeats. `since` also accepts an ISO time with an offset. `limit` is 1 to 500 (default 100). Only `agent.activity` and `policy.decided` events are in the feed.

**Deciding a Proposal.** Body:

```json
{"run_id": "replay-michaung", "decision": "approved", "decided_by": "officer-1"}
```

`decision` is `approved`, `edited` or `rejected`. An `edited` decision must also carry `action`: the edited `WorkOrder` or `WardAlertDraft` (same `kind` as the original, with its `kind` field set). `approved` and `rejected` must not carry one.

| Status | Meaning |
|---|---|
| 200 | decided; the body is the updated `Proposal`. `proposal.decided` was emitted |
| 404 `proposal_not_found` | no such Proposal in that Run |
| 409 `already_decided` | already decided by someone else or differently; `current_status` and `decided_by` say how |
| 422 | invalid body, missing `action` on an edit, an `action` on an approval, or a changed `kind` |
| 502 `event_not_sent` | the decision **was saved** but the event wasn't sent. Retry the same request: it re-sends the same event (the id derives from the Proposal), so nothing is decided twice |

Repeating the same decision by the same officer returns 200 again. `decided_at` is the Run's storm time: the wall clock for `live`; for a Replay, `Runs.sim_time`, else the newest `sim_time` in the Run's agent activity (the Replay Driver doesn't write `Runs` yet), else the Proposal's own `created_at`. It's never earlier than the Proposal.

Not built yet, blocked on the questions at the bottom of this file: `GET/POST /runs`, `GET /hit-rate`, `GET /after-action`.

## Citizen API (#7, M1 subset)

`api/citizen/`, one Lambda behind its own HTTP API (`nimbus-citizen`, stack `NimbusApi`). The base URL is the stack output `CitizenApiUrl` and the SSM parameter `/nimbus/api/citizen-url`.

An install identifies itself with the **`X-Install-Id`** header (8 to 80 characters: letters, digits, `:`, `_`, `-`). It becomes `device_id` and `reporter_id`. **There's no real auth yet** (issue #19, which swaps this for the Cognito guest identity id), so anyone can claim any id. The read routes need no header. Like the console API it is throttled to 25 requests per second per route (burst 50).

| Route | Needs install id | Body or query | Returns |
|---|---|---|---|
| `GET /segments` | no | | `Segment[]`. Static, so the app can cache it |
| `GET /risk?run_id=` | no | | `SegmentRisk[]` |
| `GET /readings?run_id=&report_id=` | no | `report_id` optional: only Readings merged from that Report | `Reading[]` |
| `POST /devices` | yes | `{"fcm_token": "...", "language": "en" \| "ta"}` | `{device_id, language}`. Registering again replaces the token |
| `GET /saved-places` | yes | | the install's `SavedPlace[]`, each plus `run_ids` |
| `PUT /saved-places/{place_id}` | yes | `{"label", "kind", "location": {lat, lon}, "radius_m"?, "run_ids"?}` | the `SavedPlace` (with `segment_ids` worked out) plus `run_ids` |
| `DELETE /saved-places/{place_id}` | yes | | `{"deleted": "<place_id>"}` |

**Saved Places.** The server works out `segment_ids`: every Segment whose line passes within `radius_m` (default 150, at most 1000) of the point, or the nearest Segment if none does and one is within 500 m. It writes the `PlaceIndex` rows the Herald reads, one per Run and Segment, and retires rows that no longer apply when a place moves or changes Runs. At most 20 places per install (409 `too_many_places`).

**`run_ids`** says which Runs alert this place. The default is `["live"]`. The demo phones should send `["replay-michaung"]`, so a Replay's alerts reach them and live users never get Replay alerts.

Not built yet (#7b): `POST /reports/upload-url`, `POST /reports`, `POST /sos`, `POST /routes`.

## FCM push sender (#6)

`api/push/`, the Lambda **`nimbus-send-push`** (name in SSM `/nimbus/lambdas/send-push`). The Herald invokes it synchronously through `agents/common/push.py`. It has its own bundle, because the Firebase Admin SDK is large.

Input: `{"run_id", "device_ids": [...], "title": {"en", "ta"}, "body": {"en", "ta"}, "data": {"k": "v"}}`. Both languages are required, `data` values must be strings, and a malformed request raises (the caller sees a `FunctionError`). Output is exactly `{"sent": n, "failed": n, "removed_tokens": n}`.

- Each device gets the text in its own `Devices.language` (English if unset). The Herald adds the `[REPLAY]` prefix; the sender sends text as given.
- A device with no `Devices` row counts as `failed`. A device whose token FCM reports as unregistered (or from another sender) is removed from `Devices`, but only if the stored token is still that one, so a refreshed token survives. Other failures never delete anything.
- Messages go out at high priority. Credentials are the Firebase service account JSON in Secrets Manager as **`nimbus/firebase`**, created by hand (issue #1), never in git. The function can read that one secret and nothing else.
- It reads and deletes `Devices` rows only.

## Event persistence

Agents and engines publish events to the bus. The console and app read DynamoDB. Nothing used to copy events into the tables, so `GET /activity`, `GET /proposals` and the rest would have read empty tables. The projector (`api/projector/`, built in #40) closes that gap.

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

`POST /proposals/{id}/decision` updates the row itself with a conditional write (`status = pending`), then emits `proposal.decided` with `source` `nimbus.console`. That makes a double approval fail cleanly, and the console sees the new status on its next 2 s poll without waiting for the projector. The projector deliberately ignores `proposal.decided`. Details are in "Console API" above.

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
