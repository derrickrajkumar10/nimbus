"""The projector copies bus events into tables, once, keyed by Run. Local only: MemoryStore and a fake resource."""

import ast
import json
import re
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from botocore.exceptions import ClientError
from nimbus_contracts.common import Agent
from nimbus_contracts.entities import Alert, Hazard, Proposal, RankedSos, Reading, Sos
from nimbus_contracts.events import (
    AgentActivity,
    AgentActivityDetail,
    AlertSent,
    ClockTick,
    HazardDetected,
    PolicyDecided,
    PolicyDecidedDetail,
    ProposalCreated,
    ReportVerified,
    SosCreated,
    SosRanked,
    SosRankedDetail,
)

from projector.core import KEYS, NOT_PROJECTED, PROJECTED, DynamoStore, MemoryStore, Put, Update, parse_eventbridge, process, project, utc_key

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "contracts" / "fixtures"
IST = timezone(timedelta(hours=5, minutes=30))
RUN = "replay-michaung"
STORM = datetime(2023, 12, 4, 2, 0, tzinfo=IST)
EMITTED = datetime(2026, 10, 11, 7, 0, tzinfo=UTC)


def fixture(name, model):
    return model.model_validate(json.loads((FIXTURES / name).read_text())[0])


def envelope(event) -> dict:
    """What EventBridge hands a Lambda for an event published by EventBridgeBus."""
    return {"detail-type": event.type, "source": f"nimbus.{event.source}", "detail": json.loads(event.model_dump_json())}


def common(event_id="ev-1", **overrides):
    return {"event_id": event_id, "run_id": RUN, "sim_time": STORM, "emitted_at": EMITTED, "source": "sentinel"} | overrides


def activity(event_id="ev-1", emitted_at=EMITTED):
    detail = AgentActivityDetail(agent=Agent.SENTINEL, saw="tick", decided="nothing", why="calm")
    return AgentActivity(**common(event_id, emitted_at=emitted_at), detail=detail)


def decided():
    detail = PolicyDecidedDetail(principal=Agent.HERALD, action="SendAlert", resource='Alert::"a-1"', allowed=True, reason="allowed")
    return PolicyDecided(**common("ev-2", source="herald"), detail=detail)


def sos_events():
    sos = fixture("sos.json", Sos)
    ranked = RankedSos(sos_id=sos.sos_id, rank=1, danger_score=88, reasons=[])
    return SosCreated(**common("ev-sos", source="triage"), detail=sos), SosRanked(
        **common("ev-rank", source="triage"), detail=SosRankedDetail(ranking=[ranked])
    )


# --- where each event lands ------------------------------------------------


def test_activity_and_policy_decisions_go_to_activity():
    store = MemoryStore()
    process(envelope(activity()), store)
    process(envelope(decided()), store)
    rows = store.rows("Activity")
    assert len(rows) == 2
    row = next(r for r in rows if r["type"] == "agent.activity")
    assert row["run_id"] == RUN
    assert row["emitted_at#event_id"] == "2026-10-11T07:00:00.000000Z#ev-1"
    assert row["detail"]["decided"] == "nothing"


@pytest.mark.parametrize(
    "event, table, key_value",
    [
        (lambda: ProposalCreated(**common(source="dispatcher"), detail=fixture("proposals.json", Proposal)), "Proposals", "proposal_id"),
        (lambda: HazardDetected(**common(source="verifier"), detail=fixture("hazards.json", Hazard)), "Hazards", "hazard_id"),
        (lambda: ReportVerified(**common(source="verifier"), detail=fixture("readings.json", Reading)), "Readings", "reading_id"),
    ],
)
def test_entity_events_go_to_their_table_keyed_by_run(event, table, key_value):
    store = MemoryStore()
    e = event()
    assert process(envelope(e), store) == 1
    (row,) = store.rows(table)
    assert row["run_id"] == RUN
    assert row[key_value] == getattr(e.detail, key_value)


def test_alert_sent_goes_to_alerts():
    alert = Alert(
        alert_id="al-1", run_id=RUN, scope="place", sent_at=STORM, segment_ids=["27480309-1"], recipient_count=2,
        message_en="Move your bike now", message_ta="இப்போது நகர்த்தவும்",
    )
    store = MemoryStore()
    process(envelope(AlertSent(**common(source="herald"), detail=alert)), store)
    (row,) = store.rows("Alerts")
    assert row["alert_id"] == "al-1" and row["message_ta"] == "இப்போது நகர்த்தவும்"


def test_floats_become_decimal_for_dynamodb():
    store = MemoryStore()
    process(envelope(ReportVerified(**common(source="verifier"), detail=fixture("readings.json", Reading))), store)
    (row,) = store.rows("Readings")
    assert isinstance(row["confidence"], Decimal)


def test_sos_ranking_is_added_to_the_sos_row():
    created, ranked = sos_events()
    store = MemoryStore()
    process(envelope(created), store)
    process(envelope(ranked), store)
    (row,) = store.rows("Sos")
    assert row["people_count"] == 3 and row["rank"] == 1 and row["danger_score"] == 88


def test_ranking_for_an_unknown_sos_creates_nothing():
    _, ranked = sos_events()
    store = MemoryStore()
    assert process(envelope(ranked), store) == 0
    assert store.rows("Sos") == []


# --- exactly once, per Run -------------------------------------------------


def test_redelivered_proposal_does_not_overwrite_a_decision():
    event = ProposalCreated(**common(source="dispatcher"), detail=fixture("proposals.json", Proposal))
    store = MemoryStore()
    process(envelope(event), store)
    (row,) = store.rows("Proposals")
    row["status"] = "approved"  # the API route decided it
    assert process(envelope(event), store) == 0
    assert store.rows("Proposals")[0]["status"] == "approved"


def test_redelivered_sos_does_not_wipe_its_ranking():
    created, ranked = sos_events()
    store = MemoryStore()
    process(envelope(created), store)
    process(envelope(ranked), store)
    assert process(envelope(created), store) == 0
    assert store.rows("Sos")[0]["rank"] == 1


def test_redelivered_activity_is_one_row():
    store = MemoryStore()
    process(envelope(activity()), store)
    process(envelope(activity()), store)
    assert len(store.rows("Activity")) == 1


def test_same_proposal_id_in_two_runs_is_two_rows():
    proposal = fixture("proposals.json", Proposal)
    store = MemoryStore()
    process(envelope(ProposalCreated(**common(source="dispatcher"), detail=proposal)), store)
    live = proposal.model_copy(update={"run_id": "live"})
    process(envelope(ProposalCreated(**common(run_id="live", source="dispatcher"), detail=live)), store)
    assert {r["run_id"] for r in store.rows("Proposals")} == {RUN, "live"}


def test_activity_keys_sort_in_time_order_across_fractions_and_offsets():
    # The event's own JSON would put 07:00:00Z after 07:00:00.500000Z.
    early = EMITTED
    late = EMITTED + timedelta(milliseconds=500)
    later_in_ist = (EMITTED + timedelta(seconds=2)).astimezone(IST)
    store = MemoryStore()
    for i, t in enumerate([late, later_in_ist, early]):
        process(envelope(activity(f"ev-{i}", emitted_at=t)), store)
    ordered = sorted(store.rows("Activity"), key=lambda r: r["emitted_at#event_id"])
    assert [r["event_id"] for r in ordered] == ["ev-2", "ev-0", "ev-1"]


def test_naive_times_are_rejected_as_keys():
    with pytest.raises(ValueError, match="timezone-aware"):
        utc_key(datetime(2026, 10, 11, 7, 0))


# --- what is not projected -------------------------------------------------


def test_events_owned_elsewhere_write_nothing():
    tick = ClockTick(**common(source="replay-driver"), tick_index=1)
    assert project(tick) == []
    assert process(envelope(tick), MemoryStore()) == 0


def test_every_event_type_is_classified():
    assert PROJECTED.isdisjoint(NOT_PROJECTED)


def test_detail_type_must_match_the_event():
    payload = envelope(activity()) | {"detail-type": "policy.decided"}
    with pytest.raises(ValueError, match="does not match"):
        parse_eventbridge(payload)


def test_malformed_detail_is_rejected_not_written():
    payload = {"detail-type": "alert.sent", "detail": {"type": "alert.sent", "run_id": "michaung"}}
    store = MemoryStore()
    with pytest.raises(Exception):
        process(payload, store)
    assert all(not rows for rows in store.tables.values())


# --- the real store, with a fake boto3 resource ----------------------------


class FakeTable:
    def __init__(self, name, fail_with=None):
        self.name, self.fail_with, self.calls = name, fail_with, []

    def put_item(self, **kwargs):
        self._call("put_item", kwargs)

    def update_item(self, **kwargs):
        self._call("update_item", kwargs)

    def _call(self, op, kwargs):
        self.calls.append((op, kwargs))
        if self.fail_with:
            raise ClientError({"Error": {"Code": self.fail_with, "Message": "x"}}, op)


class FakeResource:
    def __init__(self, fail_with=None):
        self.tables, self.fail_with = {}, fail_with

    def Table(self, name):  # noqa: N802 (boto3's name)
        return self.tables.setdefault(name, FakeTable(name, self.fail_with))


def test_dynamo_store_uses_the_named_tables_and_conditions():
    resource = FakeResource()
    store = DynamoStore(resource, {name: f"nimbus-{name}" for name in KEYS})
    created, ranked = sos_events()
    process(envelope(created), store)
    process(envelope(ranked), store)
    op, kwargs = resource.tables["nimbus-Sos"].calls[0]
    assert op == "put_item" and kwargs["Item"]["run_id"] == RUN and "ConditionExpression" in kwargs
    op, kwargs = resource.tables["nimbus-Sos"].calls[1]
    assert op == "update_item"
    assert kwargs["Key"] == {"run_id": RUN, "sos_id": "sos-0001"}
    assert kwargs["UpdateExpression"].startswith("SET ")


def test_dynamo_store_reads_table_names_from_the_environment(monkeypatch):
    monkeypatch.setenv("NIMBUS_TABLE_ACTIVITY", "nimbus-Activity")
    resource = FakeResource()
    DynamoStore(resource).apply(Put("Activity", {"run_id": RUN, "emitted_at#event_id": "k"}))
    assert "nimbus-Activity" in resource.tables


def test_failed_condition_is_a_skip_but_other_errors_are_raised():
    names = {name: name for name in KEYS}
    assert DynamoStore(FakeResource("ConditionalCheckFailedException"), names).apply(Put("Proposals", {"run_id": RUN, "proposal_id": "p"}, only_if_absent=True)) is False
    with pytest.raises(ClientError):
        DynamoStore(FakeResource("ProvisionedThroughputExceededException"), names).apply(Put("Alerts", {"run_id": RUN, "alert_id": "a"}))
    assert DynamoStore(FakeResource("ConditionalCheckFailedException"), names).apply(Update("Sos", {"run_id": RUN, "sos_id": "s"}, {"rank": 1})) is False


# --- the table keys match the storage doc ----------------------------------


def storage_md_keys() -> dict[str, tuple[str, str]]:
    keys = {}
    for line in (ROOT / "contracts" / "storage.md").read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and re.fullmatch(r"`\w+`", cells[0]):
            keys[cells[0].strip("`")] = (cells[1].strip("`"), cells[2].strip("`"))
    return keys


def test_projected_tables_use_the_keys_in_storage_md():
    documented = storage_md_keys()
    assert {name: documented[name] for name in KEYS} == KEYS


def test_the_stack_triggers_on_exactly_what_is_projected():
    """infra/stacks/api.py lists the event types and tables the projector is wired for."""
    tree = ast.parse((ROOT / "infra" / "stacks" / "api.py").read_text(encoding="utf-8"))
    wired = {
        node.targets[0].id: ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id in {"PROJECTED_EVENT_TYPES", "WRITTEN_TABLES"}
    }
    assert set(wired["PROJECTED_EVENT_TYPES"]) == PROJECTED
    assert set(wired["WRITTEN_TABLES"]) == set(KEYS)
