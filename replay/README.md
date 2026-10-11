# replay

F9 Storm Replay. **Owner: Goutam.** Michaung hourly rain from the Open-Meteo historical API, the Replay Driver that emits `clock.tick` with `sim_time` for a `replay-*` Run, simulated Reports (labelled `source: simulated`), the news-reported flooded Localities, and the Hit Rate calculation on a Prior-only Run.

## Replay Driver (minimal)

`driver.py` publishes `clock.tick` to EventBridge (`NIMBUS_EVENT_BUS`, default `nimbus`), one tick per 15 storm-minutes, `--speed` real seconds apart. Defaults: Run `replay-michaung`, start `2023-12-03T18:00:00+05:30`, 96 ticks, 2 s. It only drives `replay-*` Runs.

Before the first tick it seeds `PlaceIndex` (table name from SSM `/nimbus/tables/PlaceIndex`, or `NIMBUS_TABLE_PLACEINDEX`) for the Run, with deterministic keys, so re-seeding is safe:

- each `--demo-phone DEVICE_ID#PLACE_ID` (the real device ID from the app) on Velachery Main Road `27480309-1` and `27480309-4`;
- 150 simulated Subscribers, `sim-001#sim-place` to `sim-150#sim-place` with `simulated = true`, on `27320162-0`. That's over Cedar's 100-recipient limit, so the Herald's alert there becomes a Ward Alert Proposal.

```bash
uv run python driver.py --dry-run --ticks 4 --speed 0                 # print ticks, no AWS
uv run python driver.py --demo-phone <device_id>#<place_id>           # seed, then publish with your AWS credentials
uv run python driver.py --no-seed --start 2023-12-04T02:00:00+05:30   # resume without re-seeding
uv run pytest -q
```
