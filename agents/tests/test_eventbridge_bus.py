"""EventBridgeBus against botocore's Stubber: a fake AWS that intercepts every call
before it leaves the machine. The client has fake keys, so nothing can reach AWS."""

import json
from datetime import UTC, datetime, timedelta, timezone

import boto3
import pytest
from botocore.stub import Stubber
from nimbus_contracts.common import Agent
from nimbus_contracts.events import AgentActivity, AgentActivityDetail

from common.bus import BUS_NAME_ENV, EventBridgeBus, PublishError
from common.context import AgentContext

IST = timezone(timedelta(hours=5, minutes=30))


def fake_events_client():
    return boto3.client(
        "events", region_name="us-east-1", aws_access_key_id="fake", aws_secret_access_key="fake"
    )


def activity_event() -> AgentActivity:
    return AgentActivity(
        event_id="e-1",
        run_id="replay-michaung",
        sim_time=datetime(2023, 12, 4, 2, 0, tzinfo=IST),
        emitted_at=datetime(2026, 10, 10, 18, 0, tzinfo=UTC),
        source="herald",
        detail=AgentActivityDetail(agent=Agent.HERALD, saw="a", decided="b", why="c"),
    )


def ok_response() -> dict:
    return {"FailedEntryCount": 0, "Entries": [{"EventId": "aws-1"}]}


def test_publish_sends_the_agreed_envelope():
    client = fake_events_client()
    bus = EventBridgeBus("test-bus", client=client)
    event = activity_event()
    expected = {
        "Entries": [
            {
                "EventBusName": "test-bus",
                "Source": "nimbus.herald",
                "DetailType": "agent.activity",
                "Detail": event.model_dump_json(),
            }
        ]
    }
    with Stubber(client) as stub:
        stub.add_response("put_events", ok_response(), expected)
        bus.publish(event)
        stub.assert_no_pending_responses()


def test_detail_is_the_whole_event():
    bus = EventBridgeBus("test-bus", client=fake_events_client())
    detail = json.loads(bus.entry(activity_event())["Detail"])
    assert detail["type"] == "agent.activity"
    assert detail["run_id"] == "replay-michaung"
    assert detail["sim_time"] == "2023-12-04T02:00:00+05:30"
    assert detail["detail"]["agent"] == "herald"


def test_rejected_entry_raises_instead_of_vanishing():
    client = fake_events_client()
    bus = EventBridgeBus("test-bus", client=client)
    rejected = {
        "FailedEntryCount": 1,
        "Entries": [{"ErrorCode": "InternalFailure", "ErrorMessage": "try again"}],
    }
    with Stubber(client) as stub:
        stub.add_response("put_events", rejected)
        with pytest.raises(PublishError, match="InternalFailure"):
            bus.publish(activity_event())


def test_non_contract_event_never_reaches_aws():
    client = fake_events_client()
    bus = EventBridgeBus("test-bus", client=client)
    with Stubber(client) as stub:  # no responses queued: any AWS call would fail the test
        with pytest.raises(TypeError):
            bus.publish({"type": "agent.activity"})
        stub.assert_no_pending_responses()


def test_bus_name_comes_from_the_environment(monkeypatch):
    monkeypatch.setenv(BUS_NAME_ENV, "nimbus-from-ssm")
    assert EventBridgeBus(client=fake_events_client()).bus_name == "nimbus-from-ssm"


def test_missing_bus_name_is_a_clear_error(monkeypatch):
    monkeypatch.delenv(BUS_NAME_ENV, raising=False)
    with pytest.raises(ValueError, match=BUS_NAME_ENV):
        EventBridgeBus(client=fake_events_client())


def test_agent_context_works_on_eventbridge_too():
    # The same AgentContext from step 3, now publishing through EventBridgeBus.
    client = fake_events_client()
    bus = EventBridgeBus("test-bus", client=client)
    ctx = AgentContext.for_event(Agent.HERALD, activity_event(), bus)
    with Stubber(client) as stub:
        stub.add_response("put_events", ok_response())
        ctx.activity(saw="x", decided="y", why="z")
        stub.assert_no_pending_responses()
