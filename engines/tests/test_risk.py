"""F2 risk engine against contracts/fixtures/ Segments and the committed Michaung rain."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from nimbus_contracts.common import RiskBand
from nimbus_contracts.entities import Segment, SegmentRisk

from risk import MichaungScorer, RainSeries, load_michaung_rain, score_segments

IST = timezone(timedelta(hours=5, minutes=30))
FIXTURES = Path(__file__).resolve().parents[2] / "contracts" / "fixtures"
SCENE = datetime(2023, 12, 4, 2, 0, tzinfo=IST)  # the fixture scene


@pytest.fixture(scope="module")
def segments() -> list[Segment]:
    return [Segment.model_validate(row) for row in json.loads((FIXTURES / "segments.json").read_text())]


def bands(risks: list[SegmentRisk]) -> set[str]:
    return {r.band for r in risks}


def flat_rain(start: datetime, hours: int, mm_per_hour: float = 0.0, **overrides: float) -> RainSeries:
    """`hours` hours of rain from `start`; overrides are hour offsets ("h3": 20.0) with their own mm."""
    return RainSeries(
        {start + timedelta(hours=h + 1): overrides.get(f"h{h}", mm_per_hour) for h in range(hours)}
    )


def test_michaung_rain_is_committed_and_covers_the_storm():
    rain = load_michaung_rain()

    assert rain.covers(datetime(2023, 12, 1, 0, 0, tzinfo=IST), datetime(2023, 12, 6, 23, 0, tzinfo=IST))
    day = rain.between(datetime(2023, 12, 4, 0, 0, tzinfo=IST), datetime(2023, 12, 5, 0, 0, tzinfo=IST))
    assert day > 150  # 4 Dec was the wettest day


def test_scene_returns_valid_risk_for_every_segment(segments):
    risks = MichaungScorer()(segments, "replay-michaung", SCENE)

    assert [r.segment_id for r in risks] == [s.segment_id for s in segments]
    for risk in risks:
        assert SegmentRisk.model_validate(risk.model_dump()) == risk
        assert risk.run_id == "replay-michaung"
        assert risk.sim_time == SCENE
        assert 1 <= len(risk.reasons) <= 3
        assert risk.band != RiskBand.FLOODED


def test_scene_bands_are_sensible(segments):
    """At 02:00 the rain is steady but the deluge hasn't come: only the lowest thresholds are on watch."""
    risks = MichaungScorer()(segments, "replay-michaung", SCENE)
    by_id = {r.segment_id: r for r in risks}
    lowest = min(segments, key=lambda s: s.baseline_threshold_mm)
    highest = max(segments, key=lambda s: s.baseline_threshold_mm)

    assert bands(risks) == {"low", "watch"}
    assert by_id[lowest.segment_id].band == "watch"
    assert by_id[highest.segment_id].band == "low"
    assert by_id[lowest.segment_id].score > by_id[highest.segment_id].score
    assert all(r.reasons[0].code == "forecast_below_threshold" for r in risks)
    assert all(r.reasons[1].code == "antecedent_rain" for r in risks)  # about 100 mm since 1 Dec


@pytest.mark.parametrize(
    ("when", "expected"),
    [
        ("2023-12-02T06:00", {"low"}),  # before the storm
        ("2023-12-04T10:00", {"likely"}),  # the heaviest hours
        ("2023-12-05T12:00", {"low"}),  # after it, once the 6-hour window has drained
    ],
)
def test_bands_follow_the_storm(segments, when, expected):
    risks = MichaungScorer()(segments, "replay-michaung", datetime.fromisoformat(when).replace(tzinfo=IST))

    assert bands(risks) == expected


def test_minutes_to_flood_is_when_the_window_reaches_the_threshold(segments):
    segment = segments[0].model_copy(update={"baseline_threshold_mm": 30.0})
    now = datetime(2023, 12, 4, 2, 0, tzinfo=IST)
    # Dry for 72 h, then 20 mm an hour from `now`: 6-hour rain reaches 30 mm after 90 minutes.
    rain = flat_rain(now - timedelta(hours=72), 72 + 3, **{f"h{h}": 20.0 for h in range(72, 75)})

    [risk] = score_segments([segment], rain, "replay-michaung", now)

    assert risk.minutes_to_flood == 90
    assert risk.band == "likely"
    assert risk.reasons[0].code == "forecast_exceeds_threshold"
    assert risk.reasons[0].text == "60 mm forecast in 3 h takes 6-hour rain to 60 mm against a 30 mm threshold"
    assert risk.score == 100  # twice the threshold


def test_no_flood_expected_gives_none_and_a_low_score(segments):
    now = datetime(2023, 12, 4, 2, 0, tzinfo=IST)
    rain = flat_rain(now - timedelta(hours=72), 75, mm_per_hour=0.1)

    risks = score_segments(segments, rain, "replay-michaung", now)

    assert all(r.minutes_to_flood is None and r.band == "low" for r in risks)
    assert all(len(r.reasons) == 1 for r in risks)  # dry ground, no heavy hour


def test_already_over_the_threshold_floods_in_zero_minutes_with_every_reason(segments):
    segment = segments[0].model_copy(update={"baseline_threshold_mm": 40.0})
    now = datetime(2023, 12, 4, 2, 0, tzinfo=IST)
    rain = flat_rain(now - timedelta(hours=72), 75, mm_per_hour=12.0)  # 864 mm in 72 h

    [risk] = score_segments([segment], rain, "replay-michaung", now)

    assert risk.minutes_to_flood == 0
    assert [r.code for r in risk.reasons] == ["rain_exceeds_threshold", "antecedent_rain", "heavy_rain"]
    assert risk.reasons[1].text == "864 mm in the last 72 h; ground is saturated, so the threshold drops from 40 to 28 mm"
    assert risk.flood_threshold_mm == 40.0  # the Flood Threshold, not the wet-ground one


def test_flood_thresholds_override_the_baseline(segments):
    segment = segments[0]
    nudged = {segment.segment_id: 10.0}

    [baseline] = score_segments([segment], load_michaung_rain(), "replay-michaung", SCENE)
    [risk] = score_segments([segment], load_michaung_rain(), "replay-michaung", SCENE, flood_thresholds=nudged)

    assert risk.flood_threshold_mm == 10.0
    assert risk.score > baseline.score
    assert risk.band != RiskBand.FLOODED


def test_scoring_outside_the_rain_record_fails_loudly(segments):
    too_early = datetime(2023, 11, 29, 12, 0, tzinfo=IST)  # no Antecedent Rain record yet
    too_late = datetime(2023, 12, 6, 22, 0, tzinfo=IST)  # the 3 h forecast runs past the record
    for when in (too_early, too_late):
        with pytest.raises(ValueError, match="needs the 72 h before it and the 3 h after"):
            MichaungScorer()(segments, "replay-michaung", when)


def test_rain_within_an_hour_is_spread_evenly():
    start = datetime(2023, 12, 4, 0, 0, tzinfo=IST)
    rain = flat_rain(start, 2, h0=8.0, h1=4.0)

    assert rain.between(start, start + timedelta(minutes=15)) == pytest.approx(2.0)
    assert rain.between(start + timedelta(minutes=30), start + timedelta(minutes=90)) == pytest.approx(6.0)
    assert rain.between(start - timedelta(hours=5), start + timedelta(hours=5)) == pytest.approx(12.0)


def test_scorer_has_a_label_for_the_sentinel_feed():
    assert MichaungScorer.label == "Michaung rain, Open-Meteo archive"
