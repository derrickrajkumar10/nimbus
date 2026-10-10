"""Issue #5 "done when": a test event triggers a stub agent that passes a Cedar check
and writes an activity line. Runs entirely locally on a MemoryBus."""

import json
from datetime import UTC, datetime, timedelta, timezone

import boto3
import pytest
from nimbus_contracts.common import Agent
from nimbus_contracts.events import ClockTick
from pydantic import ValidationError

from common.bus import EventBridgeBus, MemoryBus
from common.runtime import make_handler, parse_eventbridge
from stub.handler import handle

IST = timezone(timedelta(hours=5, minutes=30))
STORM_TIME = datetime(2023, 12, 4, 2, 0, tzinfo=IST)


def tick() -> ClockTick:
    return ClockTick(
        event_id="tick-8",
        run_id="replay-michaung",
        sim_time=STORM_TIME,
        emitted_at=datetime(2026, 10, 10, 18, 0, tzinfo=UTC),
        source="replay-driver",
        tick_index=8,
    )


def delivered(entry: dict) -> dict:
    """What EventBridge hands a Lambda for a put_events entry."""
    return {
        "version": "0",
        "id": "6a7e8feb-b491-4cf7-a9f1-bf3703467718",
        "detail-type": entry["DetailType"],
        "source": entry["Source"],
        "account": "123456789012",
        "time": "2026-10-10T18:00:00Z",
        "region": "us-east-1",
        "resources": [],
        "detail": json.loads(entry["Detail"]),
    }


def tick_payload() -> dict:
    client = boto3.client("events", region_name="us-east-1", aws_access_key_id="fake", aws_secret_access_key="fake")
    return delivered(EventBridgeBus("test-bus", client=client).entry(tick()))


def test_tick_runs_stub_agent_end_to_end():
    bus = MemoryBus()
    handler = make_handler(Agent.HERALD, handle, bus=bus)

    handler(tick_payload())

    [decision] = bus.of_type("policy.decided")
    [activity] = bus.of_type("agent.activity")
    assert decision.detail.allowed is True
    assert decision.detail.reason == "allowed by herald-may-send-alerts"
    assert activity.detail.saw == "clock.tick at 04 Dec 2023 02:00"
    assert activity.detail.decided == "Would send a test Place Alert"
    for event in (decision, activity):
        assert event.run_id == "replay-michaung"
        assert event.sim_time == STORM_TIME


def test_payload_that_is_not_a_contract_event_is_rejected():
    payload = tick_payload()
    del payload["detail"]["tick_index"]
    with pytest.raises(ValidationError):
        parse_eventbridge(payload)


def test_detail_type_must_match_the_event():
    payload = tick_payload()
    payload["detail-type"] = "risk.changed"
    with pytest.raises(ValueError, match="does not match"):
        parse_eventbridge(payload)


def test_importing_the_lambda_module_needs_no_aws_setup():
    # The module-level handler creates its EventBridgeBus lazily, on first invocation.
    import stub.handler

    assert callable(stub.handler.handler)
