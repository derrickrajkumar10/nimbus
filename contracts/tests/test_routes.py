import pytest
from pydantic import ValidationError

from nimbus_contracts.routes import RouteRequest, RouteResponse, RouteStatus

LINE = {"type": "LineString", "coordinates": [[80.22, 12.98], [80.23, 12.99]]}


def response(**overrides):
    body = {
        "run_id": "replay-michaung",
        "status": "ok",
        "geometry": LINE,
        "distance_m": 1200.5,
        "duration_s": 260,
        "avoided_segment_ids": ["27480309-1"],
        "reason": "Avoids 1 street reported knee-deep.",
    }
    return body | overrides


def test_request_round_trips():
    body = {
        "run_id": "live",
        "origin": {"lat": 12.98, "lon": 80.22},
        "destination": {"lat": 12.99, "lon": 80.23},
        "vehicle": "two_wheeler",
    }
    assert RouteRequest.model_validate(body).model_dump(mode="json") == body


def test_ok_route():
    r = RouteResponse.model_validate(response())
    assert r.status == RouteStatus.OK


def test_no_safe_route_carries_no_route():
    r = RouteResponse.model_validate(
        response(status="no_safe_route", geometry=None, distance_m=None, duration_s=None, reason="Every way crosses water too deep for a car.")
    )
    assert r.geometry is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"geometry": None},
        {"distance_m": None},
        {"duration_s": None},
        {"status": "no_safe_route"},
        {"status": "no_safe_route", "geometry": None, "distance_m": 10.0, "duration_s": None},
    ],
)
def test_status_must_match_route(overrides):
    with pytest.raises(ValidationError):
        RouteResponse.model_validate(response(**overrides))


def test_run_id_and_vehicle_are_checked():
    with pytest.raises(ValidationError):
        RouteResponse.model_validate(response(run_id="michaung"))
    with pytest.raises(ValidationError):
        RouteRequest.model_validate(
            {"run_id": "live", "origin": {"lat": 1, "lon": 1}, "destination": {"lat": 1, "lon": 2}, "vehicle": "bicycle"}
        )


def test_unknown_fields_are_rejected():
    with pytest.raises(ValidationError):
        RouteResponse.model_validate(response(violation=True))
