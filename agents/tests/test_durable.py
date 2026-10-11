"""#42: SegmentRisk and PlaceIndex in DynamoDB, and deterministic IDs.

Request shapes are checked with botocore's Stubber (fake keys, nothing leaves the
machine). Behaviour across Lambda restarts uses FakeDynamo, an in-memory table
that answers the same calls.
"""

from datetime import timedelta

import boto3
import pytest
from botocore.stub import ANY, Stubber
from nimbus_contracts.common import Agent, RiskBand

from common.bus import MemoryBus
from common.context import AgentContext
from common.dynamo import from_item, to_item
from herald.subscribers import DynamoSubscribers, Subscriber
from sentinel.core import run_tick
from sentinel.fixtures import FixtureScorer, _fixture_risk, load_segments
from sentinel.reasons import ReasonWriter
from sentinel.store import DynamoRiskStore
from tests.test_herald import LIKELY_VMR, World
from tests.test_sentinel import Harness, tick


def fake_dynamo_client():
    return boto3.client("dynamodb", region_name="us-east-1", aws_access_key_id="fake", aws_secret_access_key="fake")


class FakeDynamo:
    """Just enough DynamoDB for these stores: query on the partition key, filtered scan, batch put."""

    KEYS = {"seg-risk": ("run_id", "segment_id"), "place-index": ("run_id#segment_id", "device_id#place_id")}

    def __init__(self):
        self.tables: dict[str, dict[tuple, dict]] = {name: {} for name in self.KEYS}

    def batch_write_item(self, RequestItems):
        for table, requests in RequestItems.items():
            pk, sk = self.KEYS[table]
            for r in requests:
                item = r["PutRequest"]["Item"]
                self.tables[table][(item[pk]["S"], item[sk]["S"])] = item
        return {"UnprocessedItems": {}}

    def query(self, TableName, ExpressionAttributeValues, **_):
        value = next(iter(ExpressionAttributeValues.values()))["S"]
        return {"Items": [i for (p, _), i in sorted(self.tables[TableName].items()) if p == value]}

    def scan(self, TableName, ExpressionAttributeValues, **_):
        prefix = next(iter(ExpressionAttributeValues.values()))["S"]
        return {"Items": [i for (p, _), i in self.tables[TableName].items() if p.startswith(prefix)]}


# --- item conversion -----------------------------------------------------------


def test_segment_risk_round_trips_through_a_dynamodb_item():
    risk = _fixture_risk()[0]
    item = to_item(risk)
    assert item["flood_threshold_mm"] == {"N": "67.5"}  # floats become numbers DynamoDB accepts
    assert item["sim_time"]["S"].startswith("2023-12-04T02:00:00")
    assert type(risk).model_validate(from_item(item)) == risk


# --- DynamoRiskStore -----------------------------------------------------------------


def test_save_writes_every_risk_in_one_batch():
    client = fake_dynamo_client()
    store = DynamoRiskStore("nimbus-SegmentRisk", client=client)
    risks = list(_fixture_risk())
    expected = {"RequestItems": {"nimbus-SegmentRisk": [{"PutRequest": {"Item": to_item(r)}} for r in risks]}}
    with Stubber(client) as stub:
        stub.add_response("batch_write_item", {"UnprocessedItems": {}}, expected)
        store.save(risks)
        stub.assert_no_pending_responses()


def test_save_retries_unprocessed_items():
    client = fake_dynamo_client()
    store = DynamoRiskStore("nimbus-SegmentRisk", client=client)
    [risk] = _fixture_risk()[:1]
    leftover = {"nimbus-SegmentRisk": [{"PutRequest": {"Item": to_item(risk)}}]}
    with Stubber(client) as stub:
        stub.add_response("batch_write_item", {"UnprocessedItems": leftover})
        stub.add_response("batch_write_item", {"UnprocessedItems": {}}, {"RequestItems": leftover})
        store.save([risk])
        stub.assert_no_pending_responses()


def test_latest_queries_the_run_and_follows_pages():
    client = fake_dynamo_client()
    store = DynamoRiskStore("nimbus-SegmentRisk", client=client)
    a, b = _fixture_risk()[:2]
    query = {
        "TableName": "nimbus-SegmentRisk",
        "KeyConditionExpression": "run_id = :run",
        "ExpressionAttributeValues": {":run": {"S": "replay-michaung"}},
    }
    page_key = {"run_id": {"S": "replay-michaung"}, "segment_id": {"S": a.segment_id}}
    with Stubber(client) as stub:
        stub.add_response("query", {"Items": [to_item(a)], "LastEvaluatedKey": page_key}, query)
        stub.add_response("query", {"Items": [to_item(b)]}, {**query, "ExclusiveStartKey": page_key})
        latest = store.latest("replay-michaung")
        stub.assert_no_pending_responses()
    assert latest == {a.segment_id: a, b.segment_id: b}


def test_a_restarted_sentinel_does_not_reflag_every_segment():
    """Varun's finding 1: two Lambda copies (or a cold start) share state through the table."""
    table = FakeDynamo()
    first, restarted = Harness(), Harness()
    first.store = DynamoRiskStore("seg-risk", client=table)
    restarted.store = DynamoRiskStore("seg-risk", client=table)  # new memory, same table

    flagged = first.run(tick(8))
    assert len(flagged) == sum(1 for r in _fixture_risk() if r.band != RiskBand.LOW)
    assert restarted.run(tick(9, minutes_later=15)) == []  # remembers the bands


# --- DynamoSubscribers (PlaceIndex) ----------------------------------------------------


def test_for_segment_queries_the_composite_key():
    client = fake_dynamo_client()
    subs = DynamoSubscribers("nimbus-PlaceIndex", client=client)
    expected = {
        "TableName": "nimbus-PlaceIndex",
        "KeyConditionExpression": "#pk = :pk",
        "ExpressionAttributeNames": {"#pk": "run_id#segment_id"},
        "ExpressionAttributeValues": {":pk": {"S": f"replay-michaung#{LIKELY_VMR}"}},
    }
    row = {"run_id#segment_id": {"S": f"replay-michaung#{LIKELY_VMR}"}, "device_id#place_id": {"S": "dev-1#place-home"}}
    with Stubber(client) as stub:
        stub.add_response("query", {"Items": [row]}, expected)
        assert subs.for_segment("replay-michaung", LIKELY_VMR) == [Subscriber("dev-1", "place-home")]


def test_all_in_run_scans_only_that_run_and_dedupes():
    client = fake_dynamo_client()
    subs = DynamoSubscribers("nimbus-PlaceIndex", client=client)
    row = lambda seg, dev: {"run_id#segment_id": {"S": f"replay-michaung#{seg}"}, "device_id#place_id": {"S": dev}}  # noqa: E731
    expected = {
        "TableName": "nimbus-PlaceIndex",
        "FilterExpression": "begins_with(#pk, :run)",
        "ExpressionAttributeNames": {"#pk": "run_id#segment_id"},
        "ExpressionAttributeValues": {":run": {"S": "replay-michaung#"}},
    }
    with Stubber(client) as stub:
        stub.add_response("scan", {"Items": [row("1-0", "dev-1#home")], "LastEvaluatedKey": {"x": {"S": "y"}}}, expected)
        stub.add_response("scan", {"Items": [row("2-0", "dev-1#home"), row("2-0", "dev-2#bike")]}, {**expected, "ExclusiveStartKey": {"x": {"S": "y"}}})
        assert set(subs.all_in_run("replay-michaung")) == {Subscriber("dev-1", "home"), Subscriber("dev-2", "bike")}


def test_herald_alerts_subscribers_read_from_placeindex():
    table = FakeDynamo()
    table.batch_write_item({"place-index": [{"PutRequest": {"Item": {
        "run_id#segment_id": {"S": f"replay-michaung#{LIKELY_VMR}"}, "device_id#place_id": {"S": "real-phone#place-home"},
    }}}]})
    w = World(subscribers=DynamoSubscribers("place-index", client=table))
    w.risk_changed(LIKELY_VMR, RiskBand.WATCH, RiskBand.LIKELY)
    [push] = w.sender.sent
    assert push.device_ids == ("real-phone",)


# --- deterministic IDs (finding 2) -----------------------------------------------------


def test_a_retried_tick_reproduces_the_same_event_ids():
    first, retry = Harness(), Harness()
    a = first.run(tick(8))
    b = retry.run(tick(8))  # EventBridge delivered the same tick again
    assert [e.event_id for e in a] == [e.event_id for e in b]
    assert [e.event_id for e in first.bus.events] == [e.event_id for e in retry.bus.events]


def test_different_ticks_get_different_ids():
    h = Harness()
    a = {e.event_id for e in h.bus.events} if h.run(tick(8)) else set()
    h2 = Harness()
    h2.run(tick(9, minutes_later=15))
    assert a.isdisjoint({e.event_id for e in h2.bus.events})


def test_a_retried_herald_reproduces_alert_and_proposal_ids():
    from tests.test_herald import crowd

    def run(subs):
        w = World(subscribers=subs)
        w.risk_changed(LIKELY_VMR, RiskBand.WATCH, RiskBand.LIKELY)
        return w

    place_a, place_b = run(crowd(3)), run(crowd(3))
    assert [e.detail.alert_id for e in place_a.bus.of_type("alert.sent")] == [e.detail.alert_id for e in place_b.bus.of_type("alert.sent")]
    ward_a, ward_b = run(crowd(150)), run(crowd(150))
    assert ward_a.bus.of_type("proposal.created")[0].detail.proposal_id == ward_b.bus.of_type("proposal.created")[0].detail.proposal_id


def test_record_ids_keep_their_prefix_and_time_order():
    t = tick(8)
    ctx = AgentContext.for_event(Agent.HERALD, t, MemoryBus())
    first, second = ctx.new_id("al"), ctx.new_id("al")
    assert first.startswith("al-") and first != second
    later = AgentContext.for_event(Agent.HERALD, tick(9, minutes_later=15), MemoryBus()).new_id("al")
    assert first < later
