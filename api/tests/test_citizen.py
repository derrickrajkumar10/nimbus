"""The citizen API: devices, Saved Places (and the PlaceIndex that follows them), Segments, risk, Readings."""

import ast
import json
import re
from pathlib import Path

import pytest

from citizen.geo import NEAREST_FALLBACK_M, covered_segment_ids, distance_to_line_m
from citizen.handler import handler as lambda_handler
from citizen.routes import MAX_PLACES_PER_DEVICE, Citizen
from citizen.store import TABLE_KEYS, DynamoStore, MemoryStore

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "contracts" / "fixtures"
RUN = "replay-michaung"
INSTALL = "install-demo-1"


def fixture(name):
    return json.loads((FIXTURES / name).read_text())


SEGMENTS = fixture("segments.json")
MAIN_ROAD = next(s for s in SEGMENTS if s["street_name"] == "Velachery Main Road")


def midpoint(segment):
    lon, lat = segment["geometry"]["coordinates"][len(segment["geometry"]["coordinates"]) // 2]
    return {"lat": lat, "lon": lon}


def seeded():
    store = MemoryStore()
    for s in SEGMENTS:
        store.put("Segments", s)
    for r in fixture("risk.json"):
        store.put("SegmentRisk", r)
    for r in fixture("readings.json"):
        store.put("Readings", r)
    return Citizen(store), store


def call(app, method, path, *, query=None, body=None, install=INSTALL):
    event = {
        "requestContext": {"http": {"method": method}},
        "rawPath": path,
        "queryStringParameters": query or None,
        "headers": {"X-Install-Id": install} if install else {},
        "body": json.dumps(body) if body is not None else None,
    }
    response = app.handle(event)
    return response["statusCode"], json.loads(response["body"])


def place(**overrides):
    return {"label": "Home", "kind": "home", "location": midpoint(MAIN_ROAD), "radius_m": 50} | overrides


# --- geometry --------------------------------------------------------------


def test_distance_to_a_line():
    # 0.001 deg of latitude is about 110.5 m; the point sits 1 deg-thousandth north of an east-west line.
    line = [[80.0, 13.0], [80.01, 13.0]]
    assert distance_to_line_m(13.001, 80.005, line) == pytest.approx(110.54, rel=0.01)
    assert distance_to_line_m(13.0, 80.005, line) == pytest.approx(0, abs=0.01)  # on the line
    assert distance_to_line_m(13.0, 80.02, line) == pytest.approx(0.01 * 111_320 * 0.9744, rel=0.01)  # past the end


def test_a_place_on_a_segment_covers_it_and_not_far_ones():
    ids = covered_segment_ids(midpoint(MAIN_ROAD)["lat"], midpoint(MAIN_ROAD)["lon"], 30, SEGMENTS)
    assert MAIN_ROAD["segment_id"] in ids
    assert 0 < len(ids) < len(SEGMENTS)


def test_a_bigger_radius_covers_more():
    lat, lon = midpoint(MAIN_ROAD)["lat"], midpoint(MAIN_ROAD)["lon"]
    assert set(covered_segment_ids(lat, lon, 30, SEGMENTS)) <= set(covered_segment_ids(lat, lon, 300, SEGMENTS))


def test_a_place_just_off_the_network_gets_its_nearest_segment_only_when_close():
    lat, lon = midpoint(MAIN_ROAD)["lat"], midpoint(MAIN_ROAD)["lon"]
    near = covered_segment_ids(lat + 0.0020, lon, 10, SEGMENTS)  # about 220 m off
    assert len(near) <= 1
    assert covered_segment_ids(0.0, 0.0, 10, SEGMENTS) == []  # nowhere near Chennai
    assert NEAREST_FALLBACK_M == 500


# --- devices ---------------------------------------------------------------


def test_register_a_device():
    app, store = seeded()
    status, body = call(app, "POST", "/devices", body={"fcm_token": "x" * 40, "language": "ta"})
    assert (status, body) == (200, {"device_id": INSTALL, "language": "ta"})
    assert store.get("Devices", INSTALL) == {"device_id": INSTALL, "fcm_token": "x" * 40, "language": "ta"}


def test_registering_again_replaces_the_token():
    app, store = seeded()
    call(app, "POST", "/devices", body={"fcm_token": "a" * 40, "language": "en"})
    call(app, "POST", "/devices", body={"fcm_token": "b" * 40, "language": "en"})
    assert store.get("Devices", INSTALL)["fcm_token"] == "b" * 40


@pytest.mark.parametrize("body", [{"fcm_token": "short", "language": "en"}, {"fcm_token": "x" * 40, "language": "fr"}, {"language": "en"}])
def test_bad_device_bodies(body):
    app, _ = seeded()
    assert call(app, "POST", "/devices", body=body)[0] == 422


@pytest.mark.parametrize("install", [None, "", "short", "has space in it", "bad#hash-id"])
def test_an_install_id_is_required_and_checked(install):
    app, _ = seeded()
    status, body = call(app, "POST", "/devices", body={"fcm_token": "x" * 40, "language": "en"}, install=install)
    assert (status, body["error"]) == (401, "install_id_required")


def test_cognito_identity_ids_are_accepted():
    app, _ = seeded()
    assert call(app, "GET", "/saved-places", install="us-east-1:0a1b2c3d-1111-2222-3333-444455556666")[0] == 200


# --- saved places and the index --------------------------------------------


def test_saving_a_place_computes_segments_and_indexes_them():
    app, store = seeded()
    status, body = call(app, "PUT", "/saved-places/home", body=place())
    assert status == 200 and MAIN_ROAD["segment_id"] in body["segment_ids"]
    assert body["place_id"] == "home" and body["device_id"] == INSTALL and body["run_ids"] == ["live"]
    for segment_id in body["segment_ids"]:
        row = store.get("PlaceIndex", f"live#{segment_id}", f"{INSTALL}#home")
        assert row == {"run_id#segment_id": f"live#{segment_id}", "device_id#place_id": f"{INSTALL}#home"}


def test_demo_phones_index_under_their_replay():
    app, store = seeded()
    _, body = call(app, "PUT", "/saved-places/home", body=place(run_ids=[RUN]))
    seg = body["segment_ids"][0]
    assert store.get("PlaceIndex", f"{RUN}#{seg}", f"{INSTALL}#home")
    assert store.get("PlaceIndex", f"live#{seg}", f"{INSTALL}#home") is None  # live users never get Replay alerts


def test_the_herald_can_read_the_index_it_leaves():
    # herald/subscribers.py splits the sort key on the first '#': device ids must not contain one.
    app, store = seeded()
    call(app, "PUT", "/saved-places/home", body=place(run_ids=[RUN]))
    (row,) = [r for r in store.scan("PlaceIndex")][:1]
    device_id, _, place_id = row["device_id#place_id"].partition("#")
    assert (device_id, place_id) == (INSTALL, "home")


def test_moving_a_place_retires_its_old_index_rows():
    app, store = seeded()
    other = next(s for s in SEGMENTS if s["street_name"] == "Ram Nagar Main Road")
    call(app, "PUT", "/saved-places/home", body=place(run_ids=["live"]))
    before = {k for k in store.tables["PlaceIndex"]}
    status, body = call(app, "PUT", "/saved-places/home", body=place(location=midpoint(other), run_ids=[RUN]))
    after = {k for k in store.tables["PlaceIndex"]}
    assert status == 200 and before.isdisjoint(after) and after
    assert all(pk.startswith(f"{RUN}#") for pk, _ in after)


def test_places_belong_to_their_install():
    app, _ = seeded()
    call(app, "PUT", "/saved-places/home", body=place())
    assert len(call(app, "GET", "/saved-places")[1]) == 1
    assert call(app, "GET", "/saved-places", install="install-other-9")[1] == []
    assert call(app, "DELETE", "/saved-places/home", install="install-other-9")[0] == 404


def test_listing_hides_nothing_from_the_contract_and_adds_run_ids():
    app, _ = seeded()
    call(app, "PUT", "/saved-places/home", body=place(run_ids=[RUN]))
    (view,) = call(app, "GET", "/saved-places")[1]
    assert view["label"] == "Home" and view["kind"] == "home" and view["radius_m"] == 50 and view["run_ids"] == [RUN]


def test_deleting_a_place_removes_the_index_rows_too():
    app, store = seeded()
    call(app, "PUT", "/saved-places/home", body=place(run_ids=[RUN, "live"]))
    assert store.tables["PlaceIndex"]
    assert call(app, "DELETE", "/saved-places/home") == (200, {"deleted": "home"})
    assert store.tables["PlaceIndex"] == {} and store.tables["SavedPlaces"] == {}


def test_other_installs_index_rows_survive_a_delete():
    app, store = seeded()
    call(app, "PUT", "/saved-places/home", body=place(), install="install-aaaa-1")
    call(app, "PUT", "/saved-places/home", body=place(), install="install-bbbb-2")
    call(app, "DELETE", "/saved-places/home", install="install-aaaa-1")
    assert {sk for _, sk in store.tables["PlaceIndex"]} == {"install-bbbb-2#home"}


@pytest.mark.parametrize(
    "overrides",
    [{"radius_m": 0}, {"radius_m": 5000}, {"kind": "castle"}, {"label": ""}, {"run_ids": []}, {"run_ids": ["michaung"]},
     {"location": {"lat": 99, "lon": 80}}, {"segment_ids": ["1-0"]}],
)
def test_invalid_places_are_rejected(overrides):
    app, store = seeded()
    assert call(app, "PUT", "/saved-places/home", body=place(**overrides))[0] == 422
    assert store.tables["SavedPlaces"] == {}


def test_place_ids_are_checked_and_capped():
    app, _ = seeded()
    assert call(app, "PUT", "/saved-places/bad.id", body=place())[0] == 400
    for i in range(MAX_PLACES_PER_DEVICE):
        assert call(app, "PUT", f"/saved-places/p{i}", body=place())[0] == 200
    status, body = call(app, "PUT", "/saved-places/one-too-many", body=place())
    assert (status, body["error"]) == (409, "too_many_places")
    assert call(app, "PUT", "/saved-places/p0", body=place(label="Renamed"))[0] == 200  # editing is still fine


# --- reads -----------------------------------------------------------------


def test_segments_are_served_once_and_cached():
    app, store = seeded()
    status, body = call(app, "GET", "/segments")
    assert status == 200 and len(body) == 21
    store.tables["Segments"].clear()
    assert len(call(app, "GET", "/segments")[1]) == 21  # still served from the warm cache


def test_risk_is_per_run():
    app, _ = seeded()
    assert len(call(app, "GET", "/risk", query={"run_id": RUN})[1]) == 21
    assert call(app, "GET", "/risk", query={"run_id": "live"}) == (200, [])
    assert call(app, "GET", "/risk")[1]["error"] == "run_id_required"
    assert call(app, "GET", "/risk", query={"run_id": "x"})[1]["error"] == "invalid_run_id"


def test_readings_can_be_filtered_by_report():
    app, _ = seeded()
    reading = fixture("readings.json")[0]
    assert len(call(app, "GET", "/readings", query={"run_id": RUN})[1]) == 1
    hit = call(app, "GET", "/readings", query={"run_id": RUN, "report_id": reading["report_ids"][0]})[1]
    assert [r["reading_id"] for r in hit] == [reading["reading_id"]]
    assert call(app, "GET", "/readings", query={"run_id": RUN, "report_id": "rp-nope"})[1] == []


def test_reads_need_no_install_id():
    app, _ = seeded()
    assert call(app, "GET", "/risk", query={"run_id": RUN}, install=None)[0] == 200
    assert call(app, "GET", "/segments", install=None)[0] == 200


def test_unknown_routes():
    app, _ = seeded()
    assert call(app, "GET", "/nope")[0] == 404
    assert call(app, "DELETE", "/segments")[0] == 405


# --- handler, wiring, store ------------------------------------------------


def test_lambda_handler_wiring(monkeypatch):
    import citizen.handler as h

    app, _ = seeded()
    h._citizen.cache_clear()
    monkeypatch.setattr(h, "_citizen", lambda: app)
    event = {"requestContext": {"http": {"method": "GET"}}, "rawPath": "/segments", "headers": {}}
    assert lambda_handler(event)["statusCode"] == 200


def test_the_api_stack_wires_exactly_the_routers_routes_and_tables():
    tree = ast.parse((ROOT / "infra" / "stacks" / "api.py").read_text(encoding="utf-8"))
    wired = {
        node.targets[0].id: ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id in {"CITIZEN_ROUTES", "CITIZEN_READ_TABLES", "CITIZEN_WRITE_TABLES"}
    }
    app, _ = seeded()
    assert set(map(tuple, wired["CITIZEN_ROUTES"])) == set(app.router.table)
    assert set(wired["CITIZEN_READ_TABLES"]) | set(wired["CITIZEN_WRITE_TABLES"]) == set(TABLE_KEYS)


def test_keys_match_storage_md():
    documented = {}
    for line in (ROOT / "contracts" / "storage.md").read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and re.fullmatch(r"`\w+`", cells[0]):
            documented[cells[0].strip("`")] = (cells[1].strip("`"), cells[2].strip("`") or None)
    assert {name: documented[name] for name in TABLE_KEYS} == TABLE_KEYS


class FakeTable:
    def __init__(self, pages=None):
        self.pages, self.calls = pages or [], []

    def scan(self, **kw):
        self.calls.append(("scan", kw))
        return self.pages.pop(0)

    def put_item(self, **kw):
        self.calls.append(("put_item", kw))

    def delete_item(self, **kw):
        self.calls.append(("delete_item", kw))

    def get_item(self, **kw):
        self.calls.append(("get_item", kw))
        return {}


class FakeResource:
    def __init__(self, table):
        self.table, self.names = table, []

    def Table(self, name):  # noqa: N802
        self.names.append(name)
        return self.table


def test_dynamo_store_scans_every_page_and_uses_composite_key_names():
    table = FakeTable([{"Items": [{"segment_id": "1-0"}], "LastEvaluatedKey": {"k": 1}}, {"Items": [{"segment_id": "2-0"}]}])
    store = DynamoStore(FakeResource(table), {t: f"nimbus-{t}" for t in TABLE_KEYS})
    assert [r["segment_id"] for r in store.scan("Segments")] == ["1-0", "2-0"]
    store.put("PlaceIndex", {"run_id#segment_id": "live#1-0", "device_id#place_id": "d#p"})
    store.delete("PlaceIndex", "live#1-0", "d#p")
    assert table.calls[-1][1]["Key"] == {"run_id#segment_id": "live#1-0", "device_id#place_id": "d#p"}


def test_dynamo_store_writes_floats_as_decimals(monkeypatch):
    from decimal import Decimal

    table = FakeTable()
    DynamoStore(FakeResource(table), {t: t for t in TABLE_KEYS}).put("SavedPlaces", {"device_id": "d", "place_id": "p", "radius_m": 150.5})
    assert table.calls[0][1]["Item"]["radius_m"] == Decimal("150.5")
