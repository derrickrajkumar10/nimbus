# contracts

The shapes every lane agrees on: entities, bus events, Segment IDs, a few shared rules, and real Velachery fixtures to build against before F1 exists. Terms follow [CONTEXT.md](../CONTEXT.md).

**Changing a contract:** say so in the team chat first, edit the Pydantic model, run `./generate.sh`, and commit the regenerated files with it. Don't hand-edit anything under `schema/`, `generated/` or `fixtures/`.

## What's here

| Path | What | Who uses it |
|---|---|---|
| `src/nimbus_contracts/` | Pydantic models, the source of truth | Python lanes import it: `uv add ../contracts` |
| `src/nimbus_contracts/segments.py` | `split_ways`: the only way to make Segment IDs | F1, fixtures |
| `src/nimbus_contracts/rules.py` | Score → Risk Band cut-offs, vehicle depth limits, travel modes | Sentinel, Pathfinder, app |
| `src/nimbus_contracts/routes.py` | `RouteRequest` and `RouteResponse` for `POST /routes`; `no_safe_route` carries no geometry | API, Pathfinder, app |
| `schema/` | JSON Schema, one file per entity and event, plus `nimbus.schema.json` bundling everything | Anything not in Python |
| `generated/ts/nimbus.ts` | TypeScript types, with `Event` as a discriminated union on `type` | Console |
| `generated/dart/nimbus.dart` | Dart classes with `fromJson`/`toJson` for entities | Flutter app |
| `fixtures/` | 21 real Velachery Segments with fake risk, plus a demo scene | Everyone, until real data flows |
| `storage.md` | DynamoDB table keys and S3 paths | Everyone writing to storage |

## Rules that are easy to break

- **Segment ID** is `{osm_way_id}-{n}`. Get IDs only from `split_ways`, never from your own splitting.
- **Every mutable record and every event carries `run_id`**: `live` or `replay-<name>`. Never mix Runs.
- **Never read the wall clock in domain logic.** Use the event's `sim_time`. `emitted_at` is for logs.
- **The Risk Score never produces `flooded`.** Only a Reading does.
- **Events** go on EventBridge with `detail-type` = `type`, `source` = `nimbus.<agent>`, and `detail` = the whole event.

## The fixture scene

Replay `replay-michaung` at 4 Dec 2023, 02:00 IST:

- A busy Velachery Main Road Segment is **flooded**. Three Reports were merged into a knee-deep Reading that also saw an open manhole.
- Pump 2 is free, and the Dispatcher has a pending Proposal to send it there.
- An SOS from a Ram Nagar Main Road side street has three people, one of them elderly. That's the conflict for the Commander.

Geometry, street names and building counts are real OSM data. Everything else is made up.

## Commands

```bash
./generate.sh                          # regenerate schema, fixtures, TS, Dart, then run tests
uv run pytest -q                       # tests only
```
