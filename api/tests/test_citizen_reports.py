"""POST /reports/upload-url, /reports, /sos and /routes (issue #7b)."""

import json
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest
from botocore.exceptions import ClientError

from citizen.ids import new_id
from citizen.pathfinder import LambdaPathfinder, RoutingFailed, RoutingUnavailable
from citizen.photos import CONTENT_TYPE, MemoryPhotos, S3Photos, photo_key
from citizen.routes import Citizen
from citizen.store import MemoryStore
from console.bus import MemoryBus

ROOT = Path(__file__).resolve().parents[2]
RUN = "replay-michaung"
INSTALL = "install-demo-1"
NOW = datetime(2026, 10, 11, 7, 0, tzinfo=UTC)
STORM = "2023-12-04T02:30:00+05:30"
LOCATION = {"lat": 12.9815, "lon": 80.2180}


class FakePathfinder:
    def __init__(self, answer=None, error=None):
        self.answer, self.error, self.requests = answer, error, []

    def route(self, request):
        self.requests.append(request)
        if self.error:
            raise self.error
        return self.answer


OK_ROUTE = {
    "run_id": RUN,
    "status": "ok",
    "geometry": {"type": "LineString", "coordinates": [[80.21, 12.97], [80.22, 12.98]]},
    "distance_m": 1500.0,
    "duration_s": 300,
    "avoided_segment_ids": ["27480309-1"],
    "reason": "Avoids Velachery Main Road, reported knee-deep.",
}


def build(pathfinder=None, with_clock=True):
    store, bus, photos = MemoryStore(), MemoryBus(), MemoryPhotos()
    if with_clock:
        store.put("Runs", {"run_id": RUN, "sim_time": STORM})
    app = Citizen(store, bus=bus, photos=photos, pathfinder=pathfinder, now=lambda: NOW)
    return app, store, bus, photos


def call(app, method, path, body=None, install=INSTALL):
    event = {
        "requestContext": {"http": {"method": method}},
        "rawPath": path,
        "queryStringParameters": None,
        "headers": {"x-install-id": install} if install else {},
        "body": json.dumps(body) if body is not None else None,
    }
    response = app.handle(event)
    return response["statusCode"], json.loads(response["body"])


def upload(app, photos, run_id=RUN, uploaded=True):
    status, body = call(app, "POST", "/reports/upload-url", {"run_id": run_id})
    assert status == 200
    if uploaded:
        photos.uploaded.add(body["photo_key"])
    return body


# --- reports ---------------------------------------------------------------


def test_upload_url_returns_a_fresh_id_key_and_signed_put():
    app, _, _, _ = build()
    _, body = call(app, "POST", "/reports/upload-url", {"run_id": RUN})
    assert re.fullmatch(r"rp-[0-9A-HJKMNP-TV-Z]{26}", body["report_id"])
    assert body["photo_key"] == f"reports/{RUN}/{body['report_id']}.jpg"
    assert body["method"] == "PUT" and body["headers"] == {"content-type": CONTENT_TYPE} and body["expires_in"] == 300
    assert body["upload_url"].startswith("https://")
    assert call(app, "POST", "/reports/upload-url", {"run_id": RUN})[1]["report_id"] != body["report_id"]


def test_a_report_is_stored_with_storm_time_and_announced():
    app, store, bus, photos = build()
    ticket = upload(app, photos)
    status, body = call(app, "POST", "/reports", {"report_id": ticket["report_id"], "run_id": RUN, "location": LOCATION, "note": "knee deep"})
    assert status == 200
    assert body["reporter_id"] == INSTALL and body["photo_key"] == ticket["photo_key"] and body["source"] == "app"
    assert datetime.fromisoformat(body["captured_at"]) == datetime.fromisoformat(STORM)  # the Run's clock, not the phone's
    assert store.get("Reports", RUN, ticket["report_id"])["note"] == "knee deep"
    (event,) = bus.events
    assert event.type == "report.created" and event.source == "api" and event.run_id == RUN
    assert event.detail.report_id == ticket["report_id"]


def test_a_report_needs_its_photo():
    app, store, bus, photos = build()
    ticket = upload(app, photos, uploaded=False)
    status, body = call(app, "POST", "/reports", {"report_id": ticket["report_id"], "run_id": RUN, "location": LOCATION})
    assert (status, body["error"]) == (422, "photo_not_uploaded")
    assert store.tables["Reports"] == {} and bus.events == []


def test_retrying_a_report_resends_the_same_event_and_stores_one_row():
    app, store, bus, photos = build()
    ticket = upload(app, photos)
    payload = {"report_id": ticket["report_id"], "run_id": RUN, "location": LOCATION}
    first = call(app, "POST", "/reports", payload)[1]
    again = call(app, "POST", "/reports", payload)[1]
    assert first == again and len(store.tables["Reports"]) == 1
    assert len(bus.events) == 2 and bus.events[0].event_id == bus.events[1].event_id


def test_one_install_cannot_claim_anothers_report_id():
    app, _, bus, photos = build()
    ticket = upload(app, photos)
    payload = {"report_id": ticket["report_id"], "run_id": RUN, "location": LOCATION}
    call(app, "POST", "/reports", payload)
    status, body = call(app, "POST", "/reports", payload, install="install-other-9")
    assert (status, body["error"]) == (409, "report_id_taken")
    assert len(bus.events) == 1


def test_a_replay_with_no_clock_refuses_reports_and_sos():
    app, store, bus, photos = build(with_clock=False)
    ticket = upload(app, photos)
    status, body = call(app, "POST", "/reports", {"report_id": ticket["report_id"], "run_id": RUN, "location": LOCATION})
    assert (status, body["error"]) == (409, "run_not_started")
    assert call(app, "POST", "/sos", {"run_id": RUN, "location": LOCATION, "people_count": 2})[1]["error"] == "run_not_started"
    assert bus.events == [] and store.tables["Reports"] == {}


def test_the_clock_can_come_from_agent_activity():
    app, store, _, photos = build(with_clock=False)
    store.put("Activity", {"run_id": RUN, "emitted_at#event_id": "2026-10-11T07:00:00.000000Z#ev", "sim_time": "2023-12-04T03:45:00+05:30"})
    ticket = upload(app, photos)
    _, body = call(app, "POST", "/reports", {"report_id": ticket["report_id"], "run_id": RUN, "location": LOCATION})
    assert datetime.fromisoformat(body["captured_at"]) == datetime.fromisoformat("2023-12-04T03:45:00+05:30")


def test_live_reports_use_the_wall_clock():
    app, _, _, photos = build()
    ticket = upload(app, photos, run_id="live")
    _, body = call(app, "POST", "/reports", {"report_id": ticket["report_id"], "run_id": "live", "location": LOCATION})
    assert datetime.fromisoformat(body["captured_at"]) == NOW


@pytest.mark.parametrize(
    "overrides",
    [{"report_id": "rp-short"}, {"run_id": "michaung"}, {"location": {"lat": 200, "lon": 0}}, {"note": "x" * 281}, {"photo_key": "reports/x.jpg"}],
)
def test_bad_report_bodies(overrides):
    app, _, bus, photos = build()
    ticket = upload(app, photos)
    body = {"report_id": ticket["report_id"], "run_id": RUN, "location": LOCATION} | overrides
    assert call(app, "POST", "/reports", body)[0] == 422
    assert bus.events == []


def test_report_routes_need_an_install_id():
    app, _, _, _ = build()
    assert call(app, "POST", "/reports/upload-url", {"run_id": RUN}, install=None)[0] == 401
    assert call(app, "POST", "/reports", {}, install=None)[0] == 401
    assert call(app, "POST", "/sos", {}, install=None)[0] == 401
    assert call(app, "POST", "/routes", {}, install=None)[0] == 401


def test_without_a_bucket_or_bus_the_routes_say_so():
    app = Citizen(MemoryStore())
    assert call(app, "POST", "/reports/upload-url", {"run_id": RUN})[1]["error"] == "photo_upload_unavailable"
    assert call(app, "POST", "/sos", {"run_id": "live", "location": LOCATION, "people_count": 1})[1]["error"] == "events_unavailable"
    assert call(app, "POST", "/routes", {"run_id": "live", "origin": LOCATION, "destination": LOCATION, "vehicle": "car"})[1]["error"] == "routing_unavailable"


# --- SOS -------------------------------------------------------------------


def test_sos_is_emitted_for_the_projector_not_stored_here():
    app, store, bus, _ = build()
    status, body = call(app, "POST", "/sos", {"run_id": RUN, "location": LOCATION, "people_count": 3, "flags": {"elderly": True}})
    assert status == 200 and re.fullmatch(r"sos-[0-9A-HJKMNP-TV-Z]{26}", body["sos_id"])
    assert body["reporter_id"] == INSTALL and body["people_count"] == 3 and body["flags"] == {"elderly": True, "child": False, "medical": False}
    assert datetime.fromisoformat(body["created_at"]) == datetime.fromisoformat(STORM)
    (event,) = bus.events
    assert event.type == "sos.created" and event.source == "api" and event.detail.sos_id == body["sos_id"]
    assert "Sos" not in store.tables  # the projector writes it


def test_sos_ids_sort_in_storm_order():
    early = new_id("sos", datetime.fromisoformat("2023-12-04T02:00:00+05:30"))
    late = new_id("sos", datetime.fromisoformat("2023-12-04T02:15:00+05:30"))
    assert early < late


def test_retrying_a_sos_with_its_id_resends_the_same_event():
    app, _, bus, _ = build()
    sos_id = new_id("sos", NOW)
    body = {"run_id": RUN, "location": LOCATION, "people_count": 2, "sos_id": sos_id}
    call(app, "POST", "/sos", body)
    call(app, "POST", "/sos", body)
    assert len(bus.events) == 2 and bus.events[0].event_id == bus.events[1].event_id
    assert call(app, "POST", "/sos", body)[1]["sos_id"] == sos_id


@pytest.mark.parametrize(
    "overrides", [{"people_count": 0}, {"people_count": 51}, {"flags": {"pet": True}}, {"sos_id": "sos-1"}, {"run_id": "x"}, {"photo_key": "a.jpg"}]
)
def test_bad_sos_bodies(overrides):
    app, _, bus, _ = build()
    body = {"run_id": RUN, "location": LOCATION, "people_count": 2} | overrides
    assert call(app, "POST", "/sos", body)[0] == 422
    assert bus.events == []


# --- routes ----------------------------------------------------------------


ROUTE_REQUEST = {"run_id": RUN, "origin": {"lat": 12.97, "lon": 80.21}, "destination": {"lat": 12.98, "lon": 80.22}, "vehicle": "two_wheeler"}


def test_route_asks_the_pathfinder_and_returns_its_answer():
    pathfinder = FakePathfinder(OK_ROUTE)
    app, _, _, _ = build(pathfinder)
    status, body = call(app, "POST", "/routes", ROUTE_REQUEST)
    assert status == 200 and body["status"] == "ok" and body["avoided_segment_ids"] == ["27480309-1"]
    assert pathfinder.requests == [ROUTE_REQUEST]


def test_no_safe_route_is_a_normal_answer():
    answer = {"run_id": RUN, "status": "no_safe_route", "reason": "Every way crosses water too deep for a car."}
    app, _, _, _ = build(FakePathfinder(answer))
    status, body = call(app, "POST", "/routes", ROUTE_REQUEST | {"vehicle": "car"})
    assert status == 200 and body["status"] == "no_safe_route" and body["geometry"] is None


@pytest.mark.parametrize(
    "error, status, code",
    [(RoutingUnavailable("x"), 503, "routing_unavailable"), (RoutingFailed("x"), 502, "routing_failed")],
)
def test_pathfinder_failures_map_to_http_errors(error, status, code):
    app, _, _, _ = build(FakePathfinder(error=error))
    got, body = call(app, "POST", "/routes", ROUTE_REQUEST)
    assert (got, body["error"]) == (status, code)


def test_a_malformed_pathfinder_answer_is_not_passed_on():
    app, _, _, _ = build(FakePathfinder({"status": "ok"}))
    status, body = call(app, "POST", "/routes", ROUTE_REQUEST)
    assert (status, body["error"]) == (502, "bad_route_response")


def test_route_requests_are_validated_before_calling_anything():
    pathfinder = FakePathfinder(OK_ROUTE)
    app, _, _, _ = build(pathfinder)
    assert call(app, "POST", "/routes", ROUTE_REQUEST | {"vehicle": "bicycle"})[0] == 422
    assert call(app, "POST", "/routes", ROUTE_REQUEST | {"run_id": "x"})[0] == 422
    assert pathfinder.requests == []


# --- adapters --------------------------------------------------------------


class FakeS3:
    def __init__(self, missing_code=None):
        self.missing_code, self.presigned = missing_code, []

    def generate_presigned_url(self, op, Params, ExpiresIn):  # noqa: N803
        self.presigned.append((op, Params, ExpiresIn))
        return "https://bucket.s3.amazonaws.com/signed"

    def head_object(self, Bucket, Key):  # noqa: N803
        if self.missing_code:
            raise ClientError({"Error": {"Code": self.missing_code, "Message": "x"}}, "HeadObject")
        return {}


def test_s3_photos_sign_a_jpeg_put_with_a_short_expiry():
    s3 = FakeS3()
    url = S3Photos("nimbus-photos", s3).upload_url(photo_key(RUN, "rp-X"))
    assert url.startswith("https://")
    assert s3.presigned == [("put_object", {"Bucket": "nimbus-photos", "Key": f"reports/{RUN}/rp-X.jpg", "ContentType": "image/jpeg"}, 300)]


def test_s3_photos_exists_treats_404_as_missing_and_other_errors_as_errors():
    assert S3Photos("b", FakeS3()).exists("k") is True
    assert S3Photos("b", FakeS3("404")).exists("k") is False
    with pytest.raises(ClientError):
        S3Photos("b", FakeS3("AccessDenied")).exists("k")


class FakeLambda:
    def __init__(self, payload=b"{}", function_error=None, raises=None):
        self.payload, self.function_error, self.raises, self.calls = payload, function_error, raises, []

    def invoke(self, **kw):
        self.calls.append(kw)
        if self.raises:
            raise ClientError({"Error": {"Code": self.raises, "Message": "x"}}, "Invoke")
        return {"Payload": type("P", (), {"read": lambda s: self.payload})(), **({"FunctionError": self.function_error} if self.function_error else {})}


def test_lambda_pathfinder_invokes_synchronously_and_parses_json():
    client = FakeLambda(json.dumps(OK_ROUTE).encode())
    answer = LambdaPathfinder("nimbus-pathfinder", client).route(ROUTE_REQUEST)
    assert answer["status"] == "ok"
    assert client.calls[0]["InvocationType"] == "RequestResponse" and client.calls[0]["FunctionName"] == "nimbus-pathfinder"
    assert json.loads(client.calls[0]["Payload"]) == ROUTE_REQUEST


def test_lambda_pathfinder_error_cases(monkeypatch):
    with pytest.raises(RoutingFailed):
        LambdaPathfinder("f", FakeLambda(b'{"errorMessage": "boom"}', function_error="Unhandled")).route({})
    with pytest.raises(RoutingFailed):
        LambdaPathfinder("f", FakeLambda(b"<html>")).route({})
    with pytest.raises(RoutingUnavailable):
        LambdaPathfinder("f", FakeLambda(raises="ResourceNotFoundException")).route({})
    with pytest.raises(RoutingFailed):
        LambdaPathfinder("f", FakeLambda(raises="TooManyRequestsException")).route({})
    monkeypatch.delenv("NIMBUS_PATHFINDER_FUNCTION", raising=False)
    with pytest.raises(RoutingUnavailable):
        LambdaPathfinder()


def test_every_new_id_prefix_matches_storage_md():
    storage = (ROOT / "contracts" / "storage.md").read_text(encoding="utf-8")
    assert "`rp-`" in storage and "`sos-`" in storage
