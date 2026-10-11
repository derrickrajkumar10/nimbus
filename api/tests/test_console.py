"""The console API: Run-scoped reads, one-shot decisions, and the activity feed. Local only."""

import ast
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from nimbus_contracts.entities import Proposal

from console.bus import BUS_NAME_ENV, EventBridgePublisher, MemoryBus, PublishError
from console.handler import handler as lambda_handler
from console.http import respond
from console.routes import Console
from console.store import TABLE_KEYS, DynamoStore, MemoryStore

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "contracts" / "fixtures"
RUN = "replay-michaung"
NOW = datetime(2026, 10, 11, 7, 0, tzinfo=UTC)


def fixture(name):
    return json.loads((FIXTURES / name).read_text())


def seeded() -> tuple[Console, MemoryStore, MemoryBus]:
    store, bus = MemoryStore(), MemoryBus()
    for table, name in [("SegmentRisk", "risk.json"), ("Readings", "readings.json"), ("Hazards", "hazards.json"),
                        ("Resources", "resources.json"), ("Proposals", "proposals.json"), ("Sos", "sos.json")]:
        for row in fixture(name):
            store.put(table, row)
    return Console(store, bus, now=lambda: NOW), store, bus


def call(console, method, path, query=None, body=None):
    event = {
        "requestContext": {"http": {"method": method}},
        "rawPath": path,
        "queryStringParameters": query or None,
        "body": json.dumps(body) if body is not None else None,
    }
    response = console.handle(event)
    return response["statusCode"], json.loads(response["body"])


def decision(**overrides):
    return {"run_id": RUN, "decision": "approved", "decided_by": "officer-1"} | overrides


# --- reads -----------------------------------------------------------------


@pytest.mark.parametrize(
    "path, count",
    [("/risk", 21), ("/readings", 1), ("/hazards", 1), ("/resources", 3), ("/proposals", 1), ("/sos", 1)],
)
def test_reads_return_the_runs_rows(path, count):
    console, _, _ = seeded()
    status, body = call(console, "GET", path, {"run_id": RUN})
    assert status == 200 and len(body) == count


@pytest.mark.parametrize("path", ["/risk", "/readings", "/hazards", "/resources", "/proposals", "/sos", "/activity"])
def test_every_read_needs_a_valid_run_id(path):
    console, _, _ = seeded()
    status, body = call(console, "GET", path)
    assert (status, body["error"]) == (400, "run_id_required")
    status, body = call(console, "GET", path, {"run_id": "michaung"})
    assert (status, body["error"]) == (400, "invalid_run_id")


def test_a_run_never_sees_another_runs_rows():
    console, _, _ = seeded()
    assert call(console, "GET", "/risk", {"run_id": "live"}) == (200, [])
    assert call(console, "GET", "/proposals", {"run_id": "live"}) == (200, [])


def test_pending_proposals_are_ranked():
    console, store, _ = seeded()
    first = fixture("proposals.json")[0]
    store.put("Proposals", first | {"proposal_id": "pr-0002", "rank": 2})
    store.put("Proposals", first | {"proposal_id": "pr-0003", "rank": 3, "status": "approved"})
    status, body = call(console, "GET", "/proposals", {"run_id": RUN, "status": "pending"})
    assert status == 200 and [p["proposal_id"] for p in body] == ["pr-0001", "pr-0002"]
    assert call(console, "GET", "/proposals", {"run_id": RUN, "status": "done"})[1]["error"] == "invalid_status"


def test_sos_carries_its_ranking_when_it_has_one():
    console, store, _ = seeded()
    (row,) = store.query("Sos", RUN)
    store.put("Sos", row | {"rank": 1, "danger_score": 88, "reasons": [], "merged_sos_ids": []})
    (sos,) = call(console, "GET", "/sos", {"run_id": RUN})[1]
    assert sos["rank"] == 1 and sos["danger_score"] == 88 and sos["people_count"] == 3


def test_a_row_that_breaks_the_contract_is_skipped_not_fatal():
    console, store, _ = seeded()
    store.put("Hazards", {"run_id": RUN, "hazard_id": "hz-bad", "hazard_class": "not-a-class"})
    status, body = call(console, "GET", "/hazards", {"run_id": RUN})
    assert status == 200 and [h["hazard_id"] for h in body] == ["hz-0001"]


# --- decisions -------------------------------------------------------------


def test_approve_updates_the_row_and_emits_proposal_decided():
    console, store, bus = seeded()
    status, body = call(console, "POST", "/proposals/pr-0001/decision", body=decision())
    assert status == 200 and body["status"] == "approved" and body["decided_by"] == "officer-1"
    assert store.get("Proposals", RUN, "pr-0001")["status"] == "approved"
    (event,) = bus.events
    assert event.type == "proposal.decided" and event.source == "console"
    assert event.detail.decision == "approved" and event.detail.proposal.status == "approved"
    assert event.run_id == RUN


def test_the_event_source_matches_the_agents_rule_prefix():
    # NimbusAgents rules match source prefix "nimbus."; EventBridgePublisher sends "nimbus.<source>".
    console, _, bus = seeded()
    call(console, "POST", "/proposals/pr-0001/decision", body=decision())

    class Client:
        def put_events(self, **kw):
            self.entry = kw["Entries"][0]
            return {"FailedEntryCount": 0, "Entries": [{}]}

    client = Client()
    EventBridgePublisher("nimbus", client).publish(bus.events[0])
    assert client.entry["Source"] == "nimbus.console" and client.entry["DetailType"] == "proposal.decided"
    assert json.loads(client.entry["Detail"])["detail"]["proposal_id"] == "pr-0001"


def test_decided_at_is_storm_time_not_wall_time():
    console, store, _ = seeded()
    store.put("Runs", {"run_id": RUN, "sim_time": "2023-12-04T03:15:00+05:30", "status": "running"})
    _, body = call(console, "POST", "/proposals/pr-0001/decision", body=decision())
    assert datetime.fromisoformat(body["decided_at"]) == datetime.fromisoformat("2023-12-04T03:15:00+05:30")


def test_without_a_run_clock_the_proposals_own_time_stands_in():
    console, _, _ = seeded()
    _, body = call(console, "POST", "/proposals/pr-0001/decision", body=decision())
    created = fixture("proposals.json")[0]["created_at"]
    assert datetime.fromisoformat(body["decided_at"]) == datetime.fromisoformat(created)


def test_without_a_runs_row_the_newest_activity_gives_the_storm_time():
    console, store, _ = seeded()
    for i, sim in enumerate(["2023-12-04T02:30:00+05:30", "2023-12-04T03:45:00+05:30", "2023-12-04T03:00:00+05:30"]):
        at = f"2026-10-11T07:00:0{i}.000000Z"
        store.put("Activity", {"run_id": RUN, "emitted_at#event_id": f"{at}#ev-{i}", "sim_time": sim})
    _, body = call(console, "POST", "/proposals/pr-0001/decision", body=decision())
    assert datetime.fromisoformat(body["decided_at"]) == datetime.fromisoformat("2023-12-04T03:45:00+05:30")


def test_the_runs_row_wins_over_activity():
    console, store, _ = seeded()
    store.put("Activity", {"run_id": RUN, "emitted_at#event_id": "2026-10-11T07:00:00.000000Z#ev", "sim_time": "2023-12-04T05:00:00+05:30"})
    store.put("Runs", {"run_id": RUN, "sim_time": "2023-12-04T04:00:00+05:30"})
    _, body = call(console, "POST", "/proposals/pr-0001/decision", body=decision())
    assert datetime.fromisoformat(body["decided_at"]) == datetime.fromisoformat("2023-12-04T04:00:00+05:30")


def test_live_runs_use_the_wall_clock():
    console, store, _ = seeded()
    live = fixture("proposals.json")[0] | {"run_id": "live", "created_at": "2026-10-11T06:00:00+00:00"}
    store.put("Proposals", live)
    _, body = call(console, "POST", "/proposals/pr-0001/decision", body=decision(run_id="live"))
    assert datetime.fromisoformat(body["decided_at"]) == NOW


def test_a_decision_is_never_dated_before_the_proposal():
    console, store, _ = seeded()
    store.put("Runs", {"run_id": RUN, "sim_time": "2000-01-01T00:00:00+00:00"})
    _, body = call(console, "POST", "/proposals/pr-0001/decision", body=decision())
    assert datetime.fromisoformat(body["decided_at"]) >= datetime.fromisoformat(fixture("proposals.json")[0]["created_at"])


def test_reject_and_edit():
    console, store, bus = seeded()
    assert call(console, "POST", "/proposals/pr-0001/decision", body=decision(decision="rejected"))[1]["status"] == "rejected"

    other = fixture("proposals.json")[0] | {"proposal_id": "pr-0002"}
    store.put("Proposals", other)
    edited = dict(other["action"], resource_id="rs-tree-1")
    status, body = call(console, "POST", "/proposals/pr-0002/decision", body=decision(decision="edited", action=edited))
    assert status == 200 and body["status"] == "edited" and body["action"]["resource_id"] == "rs-tree-1"
    assert store.get("Proposals", RUN, "pr-0002")["action"]["resource_id"] == "rs-tree-1"
    assert bus.events[-1].detail.proposal.action.resource_id == "rs-tree-1"


@pytest.mark.parametrize(
    "overrides, error",
    [
        ({"decision": "edited"}, "action_required"),
        ({"action": {"kind": "work_order", "resource_id": "x", "segment_id": "1-0", "buildings_affected": 1}}, "action_not_allowed"),
        ({"decision": "edited", "action": {"kind": "ward_alert", "message_en": "a", "message_ta": "b", "recipient_count": 1}}, "action_kind_changed"),
    ],
)
def test_edit_rules(overrides, error):
    console, _, bus = seeded()
    status, body = call(console, "POST", "/proposals/pr-0001/decision", body=decision(**overrides))
    assert status == 422 and body["error"] == error
    assert bus.events == []


def test_invalid_bodies_are_rejected():
    console, _, bus = seeded()
    assert call(console, "POST", "/proposals/pr-0001/decision", body={"run_id": RUN, "decision": "maybe", "decided_by": "o"})[0] == 422
    assert call(console, "POST", "/proposals/pr-0001/decision", body=decision(decided_by=""))[0] == 422
    assert call(console, "POST", "/proposals/pr-0001/decision", body=decision(extra=1))[0] == 422
    assert call(console, "POST", "/proposals/pr-0001/decision", body=decision(run_id="nope"))[0] == 422
    status, body = call(console, "POST", "/proposals/pr-0001/decision")
    assert (status, body["error"]) == (422, "invalid_decision")
    assert bus.events == []


def test_unknown_proposal_is_404_and_other_runs_are_invisible():
    console, _, _ = seeded()
    assert call(console, "POST", "/proposals/pr-9999/decision", body=decision())[0] == 404
    assert call(console, "POST", "/proposals/pr-0001/decision", body=decision(run_id="live"))[0] == 404


def test_a_second_different_decision_is_a_conflict():
    console, _, bus = seeded()
    call(console, "POST", "/proposals/pr-0001/decision", body=decision())
    status, body = call(console, "POST", "/proposals/pr-0001/decision", body=decision(decision="rejected", decided_by="officer-2"))
    assert (status, body["error"], body["current_status"]) == (409, "already_decided", "approved")
    assert len(bus.events) == 1


def test_retrying_the_same_decision_resends_the_same_event():
    console, _, bus = seeded()
    call(console, "POST", "/proposals/pr-0001/decision", body=decision())
    status, body = call(console, "POST", "/proposals/pr-0001/decision", body=decision())
    assert status == 200 and body["status"] == "approved"
    assert len(bus.events) == 2 and bus.events[0].event_id == bus.events[1].event_id


def test_a_lost_race_is_a_conflict_not_a_second_decision():
    console, store, bus = seeded()

    class Raced(MemoryStore):
        def update_proposal(self, run_id, proposal_id, values, *, only_if_status):
            # Someone else decides between our read and our write.
            super().update_proposal(run_id, proposal_id, {"status": "rejected", "decided_by": "officer-2"}, only_if_status=None)
            return super().update_proposal(run_id, proposal_id, values, only_if_status=only_if_status)

    raced = Raced()
    raced.tables = store.tables
    console = Console(raced, bus, now=lambda: NOW)
    status, body = call(console, "POST", "/proposals/pr-0001/decision", body=decision())
    assert (status, body["error"], body["decided_by"]) == (409, "already_decided", "officer-2")
    assert bus.events == []


def test_a_failed_publish_after_saving_returns_502_and_is_safe_to_retry():
    store, good = MemoryStore(), MemoryBus()
    for row in fixture("proposals.json"):
        store.put("Proposals", row)

    class Down:
        def publish(self, event):
            raise PublishError("throttled")

    import console.handler as h

    h._console.cache_clear()
    h._console = lambda: Console(store, Down(), now=lambda: NOW)
    response = lambda_handler(_event("POST", "/proposals/pr-0001/decision", body=decision()))
    assert response["statusCode"] == 502 and "retry" in json.loads(response["body"])["message"]
    assert store.get("Proposals", RUN, "pr-0001")["status"] == "approved"  # saved

    h._console = lambda: Console(store, good, now=lambda: NOW)
    response = lambda_handler(_event("POST", "/proposals/pr-0001/decision", body=decision()))
    assert response["statusCode"] == 200 and len(good.events) == 1


def _event(method, path, query=None, body=None):
    return {"requestContext": {"http": {"method": method}}, "rawPath": path, "queryStringParameters": query, "body": json.dumps(body) if body else None}


# --- activity feed ---------------------------------------------------------


def activity_rows(store, n=5):
    base = datetime(2026, 10, 11, 7, 0, tzinfo=UTC)
    for i in range(n):
        at = (base + timedelta(milliseconds=500 * i)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        store.put("Activity", {"run_id": RUN, "emitted_at#event_id": f"{at}#ev-{i}", "type": "agent.activity", "event_id": f"ev-{i}"})


def test_activity_pages_with_a_cursor():
    console, store, _ = seeded()
    activity_rows(store)
    status, first = call(console, "GET", "/activity", {"run_id": RUN, "limit": "2"})
    assert status == 200 and [i["event_id"] for i in first["items"]] == ["ev-0", "ev-1"]
    assert "emitted_at#event_id" not in first["items"][0]
    _, second = call(console, "GET", "/activity", {"run_id": RUN, "since": first["cursor"], "limit": "10"})
    assert [i["event_id"] for i in second["items"]] == ["ev-2", "ev-3", "ev-4"]
    _, empty = call(console, "GET", "/activity", {"run_id": RUN, "since": second["cursor"]})
    assert empty == {"items": [], "cursor": second["cursor"]}  # nothing new: the cursor stays


def test_activity_since_accepts_a_time_in_any_offset():
    console, store, _ = seeded()
    activity_rows(store)
    # 07:00:01 UTC written as +05:30 is the same instant, so ev-2 (07:00:01.000) onward qualifies.
    _, body = call(console, "GET", "/activity", {"run_id": RUN, "since": "2026-10-11T12:30:01+05:30"})
    assert [i["event_id"] for i in body["items"]] == ["ev-2", "ev-3", "ev-4"]


@pytest.mark.parametrize("query", [{"since": "yesterday"}, {"since": "2026-10-11T07:00:00"}, {"limit": "0"}, {"limit": "501"}, {"limit": "many"}])
def test_activity_validates_its_parameters(query):
    console, _, _ = seeded()
    assert call(console, "GET", "/activity", {"run_id": RUN} | query)[0] == 400


# --- routing, handler and wiring -------------------------------------------


def test_unknown_paths_and_methods():
    console, _, _ = seeded()
    assert call(console, "GET", "/nope", {"run_id": RUN})[0] == 404
    assert call(console, "POST", "/risk", {"run_id": RUN})[0] == 405
    assert call(console, "GET", "/proposals/pr-0001/decision", {"run_id": RUN})[0] == 405


def test_the_router_lists_the_routes_the_api_stack_must_expose():
    console, _, _ = seeded()
    assert sorted(console.router.table) == sorted(
        [("GET", p) for p in ("/risk", "/readings", "/hazards", "/resources", "/sos", "/proposals", "/activity")]
        + [("POST", "/proposals/{proposal_id}/decision")]
    )


def test_responses_are_json_with_utf8():
    assert respond(200, {"ta": "தவிர்க்கிறது"})["body"] == '{"ta": "தவிர்க்கிறது"}'


def test_publisher_needs_a_bus_name(monkeypatch):
    monkeypatch.delenv(BUS_NAME_ENV, raising=False)
    with pytest.raises(ValueError):
        EventBridgePublisher()


def test_publisher_raises_on_failed_entries():
    class Client:
        def put_events(self, **kw):
            return {"FailedEntryCount": 1, "Entries": [{"ErrorCode": "ThrottlingException", "ErrorMessage": "slow down"}]}

    console, _, bus = seeded()
    call(console, "POST", "/proposals/pr-0001/decision", body=decision())
    with pytest.raises(PublishError, match="ThrottlingException"):
        EventBridgePublisher("nimbus", Client()).publish(bus.events[0])


def test_the_api_stack_wires_exactly_the_routers_routes_and_tables():
    tree = ast.parse((ROOT / "infra" / "stacks" / "api.py").read_text(encoding="utf-8"))
    wired = {
        node.targets[0].id: ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id in {"CONSOLE_ROUTES", "CONSOLE_READ_TABLES"}
    }
    console, _, _ = seeded()
    assert set(map(tuple, wired["CONSOLE_ROUTES"])) == set(console.router.table)
    assert set(wired["CONSOLE_READ_TABLES"]) == set(TABLE_KEYS)


def test_the_dynamo_store_keys_match_storage_md():
    documented = {}
    for line in (ROOT / "contracts" / "storage.md").read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and re.fullmatch(r"`\w+`", cells[0]):
            documented[cells[0].strip("`")] = (cells[1].strip("`"), cells[2].strip("`") or None)
    assert {name: documented[name] for name in TABLE_KEYS} == TABLE_KEYS


# --- the real store, against a fake boto3 resource -------------------------


class FakeTable:
    def __init__(self, pages=None, fail=None):
        self.pages, self.fail, self.calls = pages or [], fail, []

    def query(self, **kw):
        self.calls.append(("query", kw))
        return self.pages.pop(0)

    def get_item(self, **kw):
        self.calls.append(("get_item", kw))
        return {"Item": {"run_id": "live", "sim_time": "x"}}

    def update_item(self, **kw):
        from botocore.exceptions import ClientError

        self.calls.append(("update_item", kw))
        if self.fail:
            raise ClientError({"Error": {"Code": self.fail, "Message": "x"}}, "UpdateItem")


class FakeResource:
    def __init__(self, table):
        self.table, self.names = table, []

    def Table(self, name):  # noqa: N802
        self.names.append(name)
        return self.table


def test_dynamo_store_follows_pagination_and_converts_decimals():
    from decimal import Decimal

    table = FakeTable([
        {"Items": [{"run_id": "live", "score": Decimal("7"), "ratio": Decimal("0.5")}], "LastEvaluatedKey": {"k": 1}},
        {"Items": [{"run_id": "live", "score": Decimal("9")}]},
    ])
    store = DynamoStore(FakeResource(table), {name: f"nimbus-{name}" for name in TABLE_KEYS})
    rows = store.query("SegmentRisk", "live")
    assert [r["score"] for r in rows] == [7, 9] and rows[0]["ratio"] == 0.5
    assert table.calls[1][1]["ExclusiveStartKey"] == {"k": 1}


def test_dynamo_store_can_read_newest_first():
    table = FakeTable([{"Items": []}])
    DynamoStore(FakeResource(table), {name: name for name in TABLE_KEYS}).query("Activity", "live", limit=20, newest_first=True)
    assert table.calls[0][1]["ScanIndexForward"] is False


def test_dynamo_store_activity_query_is_exclusive_and_limited():
    table = FakeTable([{"Items": []}])
    DynamoStore(FakeResource(table), {name: name for name in TABLE_KEYS}).query("Activity", "live", after="k", limit=5)
    kwargs = table.calls[0][1]
    assert kwargs["Limit"] == 5 and "KeyConditionExpression" in kwargs


def test_dynamo_store_update_is_conditional_on_pending():
    table = FakeTable()
    store = DynamoStore(FakeResource(table), {name: name for name in TABLE_KEYS})
    assert store.update_proposal("live", "pr-1", {"status": "approved"}, only_if_status="pending") is True
    kwargs = table.calls[0][1]
    assert kwargs["Key"] == {"run_id": "live", "proposal_id": "pr-1"} and "ConditionExpression" in kwargs
    assert kwargs["ExpressionAttributeNames"] == {"#a0": "status"}  # status is a reserved word

    assert DynamoStore(FakeResource(FakeTable(fail="ConditionalCheckFailedException")), {n: n for n in TABLE_KEYS}).update_proposal(
        "live", "pr-1", {"status": "approved"}, only_if_status="pending"
    ) is False


def test_dynamo_store_reads_table_names_from_the_environment(monkeypatch):
    monkeypatch.setenv("NIMBUS_TABLE_RUNS", "nimbus-Runs")
    resource = FakeResource(FakeTable())
    assert DynamoStore(resource).get("Runs", "live") == {"run_id": "live", "sim_time": "x"}
    assert resource.names == ["nimbus-Runs"]
