"""Where agents publish events.

MemoryBus keeps events in a list for local runs and tests. EventBridgeBus sends
the same events to Amazon EventBridge, mapped as contracts/README.md specifies:
detail-type = event.type, source = "nimbus.<source>", detail = the whole event.
"""

import os
from typing import Any, Protocol

from nimbus_contracts.events import EVENT_TYPES

# Set on each agent Lambda from the SSM parameter NimbusShared publishes; never hard-coded.
BUS_NAME_ENV = "NIMBUS_EVENT_BUS"

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


class PublishError(RuntimeError):
    pass


class EventBridgeBus:
    """Publishes events to an EventBridge bus.

    `client` is a boto3 "events" client; tests pass one wrapped in botocore's Stubber
    so nothing leaves the machine.
    """

    def __init__(self, bus_name: str | None = None, client: Any = None) -> None:
        self.bus_name = bus_name or os.environ.get(BUS_NAME_ENV)
        if not self.bus_name:
            raise ValueError(f"no EventBridge bus name: pass bus_name or set {BUS_NAME_ENV}")
        self._client = client

    @property
    def client(self) -> Any:
        if self._client is None:
            import boto3

            self._client = boto3.client("events")
        return self._client

    def entry(self, event: Any) -> dict[str, str]:
        return {
            "EventBusName": self.bus_name,
            "Source": f"nimbus.{event.source}",
            "DetailType": event.type,
            "Detail": event.model_dump_json(),
        }

    def publish(self, event: object) -> None:
        ensure_contract_event(event)
        response = self.client.put_events(Entries=[self.entry(event)])
        # put_events reports rejected entries in the response instead of raising.
        if response.get("FailedEntryCount", 0):
            failed = response["Entries"][0]
            raise PublishError(
                f"EventBridge rejected {event.type}: {failed.get('ErrorCode')} {failed.get('ErrorMessage')}"
            )
