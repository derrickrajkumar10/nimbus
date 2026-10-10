"""Where agents publish events.

MemoryBus keeps events in a list for local runs and tests. The EventBridge
publisher comes later and must accept exactly the same events.
"""

from typing import Protocol

from nimbus_contracts.events import EVENT_TYPES

_CONTRACT_EVENTS = tuple(EVENT_TYPES)


def ensure_contract_event(event: object) -> None:
    """Reject anything that isn't a nimbus_contracts event, so a bad shape never reaches the bus."""
    if not isinstance(event, _CONTRACT_EVENTS):
        raise TypeError(f"only nimbus_contracts events can be published, got {type(event).__name__}")


class Bus(Protocol):
    def publish(self, event: object) -> None: ...


class MemoryBus:
    """A fake bus: events are appended to `events` instead of going to AWS."""

    def __init__(self) -> None:
        self.events: list = []

    def publish(self, event: object) -> None:
        ensure_contract_event(event)
        self.events.append(event)

    def of_type(self, event_type: str) -> list:
        return [e for e in self.events if e.type == event_type]
