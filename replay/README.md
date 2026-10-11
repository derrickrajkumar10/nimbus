# replay

F9 Storm Replay. **Owner: Goutam.** Michaung hourly rain from the Open-Meteo historical API, the Replay Driver that emits `clock.tick` with `sim_time` for a `replay-*` Run, simulated Reports (labelled `source: simulated`), the news-reported flooded Localities, and the Hit Rate calculation on a Prior-only Run.

## Replay Driver (minimal)

`driver.py` publishes `clock.tick` to EventBridge (`NIMBUS_EVENT_BUS`, default `nimbus`), one tick per 15 storm-minutes, `--speed` real seconds apart. Defaults: Run `replay-michaung`, start `2023-12-03T18:00:00+05:30`, 96 ticks, 2 s.

```bash
uv run python driver.py --dry-run --ticks 4 --speed 0   # print ticks, no AWS
uv run python driver.py --ticks 96                      # publish with your AWS credentials
uv run pytest -q
```
