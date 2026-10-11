from datetime import UTC, datetime, timedelta, timezone

import pytest
from nimbus_contracts.common import Agent
from nimbus_contracts.entities import AlertScope
from nimbus_contracts.events import ClockTick, Event
from pydantic import TypeAdapter

from common.bus import MemoryBus
from common.context import AgentContext

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


def herald_context() -> tuple[AgentContext, MemoryBus]:
    bus = MemoryBus()
    return AgentContext.for_event(Agent.HERALD, tick(), bus), bus


def test_cedar_check_allowed_is_returned_and_recorded():
    ctx, bus = herald_context()
    attrs = {"scope": AlertScope.PLACE.value, "recipient_count": 12}

    decision = ctx.cedar_check("SendAlert", 'Alert::"a-1"', resource_attrs=attrs)

    assert decision.allowed
    [event] = bus.of_type("policy.decided")
    assert event.detail.principal == "herald"
    assert event.detail.action == "SendAlert"
    assert event.detail.resource == 'Alert::"a-1"'
    assert event.detail.allowed is True
    assert "herald-may-send-alerts" in event.detail.reason


def test_cedar_check_denied_is_recorded_too():
    ctx, bus = herald_context()
    attrs = {"scope": AlertScope.WARD.value, "recipient_count": 4000}

    decision = ctx.cedar_check("SendAlert", 'Alert::"a-2"', resource_attrs=attrs)

    assert not decision.allowed
    [event] = bus.of_type("policy.decided")
    assert event.detail.allowed is False
    assert "ward-alerts-need-approval" in event.detail.reason


def test_activity_line():
    ctx, bus = herald_context()

    ctx.activity(saw="Velachery Main Road went to likely", decided="Alert 12 Subscribers", why="Band went up")

    [event] = bus.of_type("agent.activity")
    assert event.detail.agent == "herald"
    assert event.detail.saw == "Velachery Main Road went to likely"
    assert event.detail.decided == "Alert 12 Subscribers"
    assert event.detail.why == "Band went up"


def test_emitted_events_inherit_run_and_storm_time_from_trigger():
    ctx, bus = herald_context()
    ctx.activity(saw="a", decided="b", why="c")
    ctx.cedar_check("ReadSOS", 'Sos::"sos-1"')

    assert len(bus.events) == 2
    for event in bus.events:
        assert event.run_id == "replay-michaung"
        assert event.sim_time == STORM_TIME  # storm time, not the laptop's clock
        assert event.source == "herald"
    assert bus.events[0].event_id != bus.events[1].event_id


def test_emitted_events_match_the_shared_contract():
    # Round-trip through JSON and the contracts' Event union, as the console will read them.
    ctx, bus = herald_context()
    ctx.activity(saw="a", decided="b", why="c")
    ctx.cedar_check("SendAlert", 'Alert::"a-1"', resource_attrs={"scope": "place", "recipient_count": 1})

    adapter = TypeAdapter(Event)
    for event in bus.events:
        parsed = adapter.validate_json(event.model_dump_json())
        assert parsed == event


def test_bus_rejects_anything_that_is_not_a_contract_event():
    bus = MemoryBus()
    with pytest.raises(TypeError):
        bus.publish({"type": "agent.activity", "detail": {"agent": "herald"}})
    assert bus.events == []
