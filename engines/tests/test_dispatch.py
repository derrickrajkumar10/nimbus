"""Dispatch solver against contracts/fixtures/ (Michaung, 4 Dec 2023 02:00 IST)."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from nimbus_contracts.common import GeoPoint
from nimbus_contracts.entities import Reading, Resource, Segment, SegmentRisk, Sos

from dispatch import rank_work_orders
from dispatch.solver import FLOOD_SPEED_KMH

IST = timezone(timedelta(hours=5, minutes=30))
FIXTURES = Path(__file__).resolve().parents[2] / "contracts" / "fixtures"
RUN = "replay-michaung"
SCENE = datetime(2023, 12, 4, 2, 0, tzinfo=IST)


def load(name, model):
    return [model.model_validate(row) for row in json.loads((FIXTURES / f"{name}.json").read_text())]


@pytest.fixture(scope="module")
def scene():
    return {
        "segments": load("segments", Segment),
        "risks": load("risk", SegmentRisk),
        "resources": load("resources", Resource),
        "readings": load("readings", Reading),
        "sos": load("sos", Sos),
    }


def rank(scene, **overrides):
    inputs = {**scene, **overrides}
    return rank_work_orders(
        inputs["segments"], inputs["risks"], inputs["resources"], inputs["readings"], inputs["sos"], run_id=RUN, sim_time=SCENE
    )


def free(resources):
    return [r.model_copy(update={"status": "free"}) for r in resources]


def test_pump_2_goes_to_velachery_main_road_first_with_its_numbers(scene):
    first = rank(scene)[0]

    assert (first.resource_id, first.segment_id, first.rank) == ("rs-pump-2", "27480309-1", 1)
    assert first.buildings_affected == 17
    assert first.reading_ids == ("rd-0001",)
    assert first.numbers["band_weight"] == 2.0  # flooded
    assert first.numbers["impact"] == (17 + 10) * 2.0  # buildings + one Reading, doubled for flooded
    assert first.travel_minutes == pytest.approx(first.numbers["distance_km"] / FLOOD_SPEED_KMH * 60, abs=0.1)
    assert first.score == pytest.approx(first.numbers["impact"] / (first.travel_minutes + 5), rel=0.01)
    assert first.reason.startswith("Send Pump 2 to Velachery Main Road: flooded, about 17 buildings nearby")


def test_tree_crews_and_busy_pumps_are_not_sent_to_water(scene):
    ranked = rank(scene)

    assert [c.resource_id for c in ranked] == ["rs-pump-2"]  # Pump 1 is working; Tree crew 1 has no tree Hazard


def test_no_free_resources_gives_nothing(scene):
    busy = [r.model_copy(update={"status": "working"}) for r in scene["resources"]]

    assert rank(scene, resources=busy) == []


def test_pumps_are_never_sent_to_watch_or_low_segments(scene):
    calm = [r.model_copy(update={"band": "watch" if r.score >= 40 else "low"}) for r in scene["risks"]]
    assert rank(scene, risks=calm) == []

    ranked = rank(scene, resources=free(scene["resources"]))
    bands = {r.segment_id: r.band for r in scene["risks"]}
    assert ranked and all(bands[c.segment_id] in ("flooded", "likely") for c in ranked)


def test_each_resource_and_segment_is_used_once(scene):
    ranked = rank(scene, resources=free(scene["resources"]))

    assert [c.rank for c in ranked] == list(range(1, len(ranked) + 1))
    assert len({c.resource_id for c in ranked}) == len(ranked)
    assert len({c.segment_id for c in ranked}) == len(ranked)
    assert {c.segment_id for c in ranked} == {"27480309-1", "27480309-4"}  # the only flooded and likely Segments
    assert ranked[0].score >= ranked[1].score


def test_output_is_deterministic(scene):
    resources = free(scene["resources"])
    first = rank(scene, resources=resources)

    assert rank(scene, resources=list(reversed(resources)), segments=list(reversed(scene["segments"]))) == first
    assert [c.numbers for c in rank(scene, resources=resources)] == [c.numbers for c in first]


def test_sos_near_a_segment_adds_to_its_impact(scene):
    flooded = next(s for s in scene["segments"] if s.segment_id == "27480309-1")
    lon, lat = flooded.geometry.coordinates[0]
    near = scene["sos"][0].model_copy(update={"location": GeoPoint(lat=lat, lon=lon)})

    first = rank(scene, sos=[near])[0]

    assert first.sos_ids == ("sos-0001",)
    assert first.numbers["sos_weight"] == 3 * 5 + 10  # three people, one elderly
    assert "3 people in 1 SOS nearby" in first.reason


def test_other_runs_and_later_readings_are_ignored(scene):
    later = scene["readings"][0].model_copy(update={"observed_at": SCENE + timedelta(minutes=5)})
    other_run = [r.model_copy(update={"run_id": "live"}) for r in scene["resources"]]

    assert rank(scene, readings=[later])[0].reading_ids == ()
    assert rank(scene, resources=other_run) == []
