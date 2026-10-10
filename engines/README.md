# engines

Deterministic Python, no LLM. **Owner: Goutam.**

- `terrain/`: F1 sink map. Runs once offline, uses `nimbus_contracts.segments.split_ways`, and writes versioned GeoJSON to S3 plus `Segments` rows.
- `risk/`: F2 risk engine. One function from (Segments, rain, Antecedent Rain, tide, Readings, `sim_time`) to `SegmentRisk`. Use `rules.band_for_score`.
- `router/`: F6 avoid-zone builder and the Amazon Location call (ADR 0003). Called by the Pathfinder.
- `dispatch/`: greedy Work Order solver. Called by the Dispatcher.
