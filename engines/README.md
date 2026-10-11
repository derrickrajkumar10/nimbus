# engines

Deterministic Python, no LLM. **Owner: Goutam.**

- `terrain/`: F1 sink map. Runs once offline, uses `nimbus_contracts.segments.split_ways`, and writes versioned GeoJSON to S3 plus `Segments` rows.
- `risk/`: F2 risk engine. One function from (Segments, rain, Antecedent Rain, tide, Readings, `sim_time`) to `SegmentRisk`. Use `rules.band_for_score`.
- `router/`: F6 avoid-zone builder and the Amazon Location call (ADR 0003). Called by the Pathfinder.
- `dispatch/`: greedy Work Order solver. Called by the Dispatcher.

## Risk engine (minimal)

`risk.score_segments(segments, rain, run_id, sim_time, *, flood_thresholds=None)` is pure. `risk.MichaungScorer` is the Sentinel's Scorer for the Michaung Replay: it reads `risk/michaung_rain.json` (Open-Meteo archive, Velachery, 28 Nov–6 Dec 2023) and calls `score_segments`. The rules are in the `risk/score.py` docstring. Tide and Readings are not used yet.

```bash
uv run pytest -q
```

## Dispatch solver (minimal)

`dispatch.rank_work_orders(segments, risks, resources, readings=(), sos=(), *, run_id, sim_time)` is pure and returns ranked `Candidate` Work Orders, each with the numbers behind it and a one-sentence reason.

- **Needs:** Segments in `flooded` or `likely`. Only `free` Resources. Pumps go to water; tree crews never do (fallen-tree Hazards aren't an input yet).
- **impact** = (`buildings_nearby` + 10 per Reading + SOS weight) × band weight (`flooded` 2, `likely` 1). An SOS within 150 m of a Segment vertex weighs 5 per person, plus 10 if anyone is elderly, a child or needs medical help.
- **travel_minutes** = haversine km from the Resource to the Segment's first coordinate ÷ `FLOOD_SPEED_KMH` (15) × 60.
- **score** = impact ÷ (travel_minutes + 5).
- **Greedy:** highest score first, each Resource once, each Segment at most one Resource. Ties break by `segment_id`, then `resource_id`.
