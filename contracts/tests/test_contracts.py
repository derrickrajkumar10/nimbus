import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

from nimbus_contracts.entities import (
    Hazard,
    Proposal,
    Reading,
    Resource,
    Segment,
    SegmentRisk,
    Sos,
)
from nimbus_contracts.events import Event, RiskChanged
from nimbus_contracts.routes import RouteRequest, RouteResponse

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "fixtures"


@pytest.mark.parametrize(
    "name, model",
    [
        ("segments.json", Segment),
        ("risk.json", SegmentRisk),
        ("readings.json", Reading),
        ("hazards.json", Hazard),
        ("resources.json", Resource),
        ("proposals.json", Proposal),
        ("sos.json", Sos),
        ("route_requests.json", RouteRequest),
        ("routes.json", RouteResponse),
    ],
)
def test_fixtures_match_contracts(name, model):
    rows = json.loads((FIXTURES / name).read_text())
    assert rows
    TypeAdapter(list[model]).validate_python(rows)


def test_fixture_references_resolve():
    segment_ids = {s["segment_id"] for s in json.loads((FIXTURES / "segments.json").read_text())}
    for row in json.loads((FIXTURES / "risk.json").read_text()) + json.loads((FIXTURES / "readings.json").read_text()):
        assert row["segment_id"] in segment_ids
    for p in json.loads((FIXTURES / "proposals.json").read_text()):
        assert p["action"]["segment_id"] in segment_ids


def test_flooded_band_only_where_a_reading_exists():
    reading_segments = {r["segment_id"] for r in json.loads((FIXTURES / "readings.json").read_text())}
    for row in json.loads((FIXTURES / "risk.json").read_text()):
        if row["band"] == "flooded":
            assert row["segment_id"] in reading_segments


def _risk_changed(**overrides):
    event = {
        "type": "risk.changed",
        "event_id": "ev-1",
        "run_id": "replay-michaung",
        "sim_time": "2023-12-04T02:00:00+05:30",
        "emitted_at": "2026-10-11T01:00:00+05:30",
        "source": "sentinel",
        "detail": {
            "segment_id": "27480309-1",
            "previous_band": "watch",
            "band": "likely",
            "score": 74,
            "minutes_to_flood": 90,
            "reasons": [],
        },
    }
    return event | overrides


def test_event_union_dispatches_on_type():
    assert isinstance(TypeAdapter(Event).validate_python(_risk_changed()), RiskChanged)


@pytest.mark.parametrize(
    "overrides",
    [
        {"run_id": "michaung"},  # must be "live" or "replay-..."
        {"sim_time": "2023-12-04T02:00:00"},  # sim_time must carry a timezone
        {"unexpected": 1},  # no silent extra fields
    ],
)
def test_events_reject_contract_drift(overrides):
    with pytest.raises(ValidationError):
        TypeAdapter(Event).validate_python(_risk_changed(**overrides))


def test_schema_files_are_current():
    from tools.export_schema import main

    assert main(check=True) == 0, "run: uv run python tools/export_schema.py"
