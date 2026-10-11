"""F2 risk engine (#4), minimal: rain against each Segment's Flood Threshold.

A Flood Threshold is the rain over a rolling 6-hour window at which a Segment floods.
At each `sim_time` the engine looks 3 hours ahead in 15-minute steps:

- Antecedent Rain (the last 72 h) lowers the effective threshold, by up to 30% once
  the ground is saturated.
- `minutes_to_flood` is the first step where the 6-hour rain reaches the effective
  threshold, or None if it doesn't within 3 hours.
- The Risk Score is the peak 6-hour rain over those 3 hours as a share of the
  effective threshold, scaled so that reaching it is exactly `likely`. The score never
  yields `flooded`; only a Reading does.

Tide and Readings are not used yet. In a Replay the "forecast" is the archive's own
later hours, so it is a perfect forecast.
"""

from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta

from nimbus_contracts.common import Reason
from nimbus_contracts.entities import Segment, SegmentRisk
from nimbus_contracts.rules import LIKELY_FROM, band_for_score

from risk.rain import HOUR, RainSeries

WINDOW = timedelta(hours=6)  # the rolling window Flood Thresholds are measured over
HORIZON = timedelta(hours=3)  # how far ahead the forecast looks
STEP = timedelta(minutes=15)  # resolution of minutes_to_flood
ANTECEDENT = timedelta(hours=72)

WET_MM = 50.0  # Antecedent Rain from which the ground counts as wet
SATURATED_MM = 150.0  # ... and as saturated, where the threshold drop is largest
WET_GROUND_DROP = 0.3  # saturated ground lowers the effective threshold by 30%
HEAVY_HOUR_MM = 10.0  # an hour this wet is worth a reason of its own


def score_segments(
    segments: Sequence[Segment],
    rain: RainSeries,
    run_id: str,
    sim_time: datetime,
    *,
    flood_thresholds: Mapping[str, float] | None = None,
) -> list[SegmentRisk]:
    """Score every Segment at `sim_time`. Pure: no I/O, no wall clock.

    `flood_thresholds` holds this Run's Flood Thresholds after Reading nudges, by
    segment_id; a Segment missing from it uses its Baseline Threshold.
    """
    if not rain.covers(sim_time - ANTECEDENT, sim_time + HORIZON):
        raise ValueError(
            f"rain covers {rain.start:%d %b %H:%M} to {rain.end:%d %b %H:%M}; scoring {sim_time:%d %b %H:%M} "
            f"needs the 72 h before it and the 3 h after"
        )
    flood_thresholds = flood_thresholds or {}

    # The rain is the same for every Segment, so work it out once.
    steps = int(HORIZON / STEP)
    windows = [rain.between(sim_time + k * STEP - WINDOW, sim_time + k * STEP) for k in range(steps + 1)]
    peak = max(windows)
    forecast = rain.between(sim_time, sim_time + HORIZON)
    antecedent = rain.between(sim_time - ANTECEDENT, sim_time)
    last_hour = rain.between(sim_time - HOUR, sim_time)
    wetness = 1 - WET_GROUND_DROP * min(antecedent / SATURATED_MM, 1.0)

    risks = []
    for segment in segments:
        threshold = flood_thresholds.get(segment.segment_id, segment.baseline_threshold_mm)
        effective = threshold * wetness
        crossing = next((k for k, mm in enumerate(windows) if mm >= effective), None)
        minutes_to_flood = None if crossing is None else int(crossing * STEP / timedelta(minutes=1))
        score = _score(peak / effective)

        reasons = [_rain_reason(minutes_to_flood, windows[0], forecast, peak, effective)]
        if antecedent >= WET_MM:
            ground = "saturated" if antecedent >= SATURATED_MM else "wet"
            reasons.append(
                Reason(
                    code="antecedent_rain",
                    text=f"{antecedent:.0f} mm in the last 72 h; ground is {ground}, "
                    f"so the threshold drops from {threshold:.0f} to {effective:.0f} mm",
                )
            )
        if last_hour >= HEAVY_HOUR_MM:
            reasons.append(Reason(code="heavy_rain", text=f"{last_hour:.0f} mm fell in the last hour"))

        risks.append(
            SegmentRisk(
                run_id=run_id,
                segment_id=segment.segment_id,
                sim_time=sim_time,
                score=score,
                band=band_for_score(score),
                minutes_to_flood=minutes_to_flood,
                reasons=reasons,
                flood_threshold_mm=threshold,
            )
        )
    return risks


def _score(ratio: float) -> int:
    """0 to 69 while the rain stays under the threshold, 70 (`likely`) at it, 100 at twice it."""
    if ratio < 1:
        return min(LIKELY_FROM - 1, int(LIKELY_FROM * ratio))
    return min(100, LIKELY_FROM + int((100 - LIKELY_FROM) * (ratio - 1)))


def _rain_reason(minutes_to_flood: int | None, past: float, forecast: float, peak: float, effective: float) -> Reason:
    if minutes_to_flood == 0:
        return Reason(code="rain_exceeds_threshold", text=f"{past:.0f} mm in the last 6 h against a {effective:.0f} mm threshold")
    if minutes_to_flood is not None:
        return Reason(
            code="forecast_exceeds_threshold",
            text=f"{forecast:.0f} mm forecast in 3 h takes 6-hour rain to {peak:.0f} mm against a {effective:.0f} mm threshold",
        )
    return Reason(
        code="forecast_below_threshold",
        text=f"{forecast:.0f} mm forecast in 3 h; 6-hour rain peaks at {peak:.0f} mm against a {effective:.0f} mm threshold",
    )
