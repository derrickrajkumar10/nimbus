"""Turn an agent's `handle(ctx, event)` into a Lambda handler.

EventBridge invokes the Lambda with its own envelope ("detail-type", "source",
"time", ...). The contract event is the envelope's `detail`, because
EventBridgeBus publishes the whole event there.
"""

from collections.abc import Callable
from typing import Any

from nimbus_contracts.common import Agent
from nimbus_contracts.events import Event
from pydantic import TypeAdapter

from common.bus import Bus, EventBridgeBus
from common.context import AgentContext

_EVENT = TypeAdapter(Event)

Handle = Callable[[AgentContext, Any], None]


def parse_eventbridge(payload: dict[str, Any]) -> Any:
    """The contract event inside an EventBridge envelope. Raises if it isn't a valid one."""
    event = _EVENT.validate_python(payload["detail"])
    if payload.get("detail-type") != event.type:
        raise ValueError(f"detail-type {payload.get('detail-type')!r} does not match event type {event.type!r}")
    return event


def make_handler(agent: Agent, handle: Handle, bus: Bus | None = None) -> Callable[..., None]:
    """A Lambda handler that parses the event and runs `handle` with an AgentContext.

    Without `bus`, an EventBridgeBus is created on first use and reused while the
    Lambda stays warm. Tests pass a MemoryBus.
    """

    def handler(payload: dict[str, Any], lambda_context: Any = None) -> None:
        nonlocal bus
        if bus is None:
            bus = EventBridgeBus()
        event = parse_eventbridge(payload)
        handle(AgentContext.for_event(agent, event, bus), event)

    return handler
