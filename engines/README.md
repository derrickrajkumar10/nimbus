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
