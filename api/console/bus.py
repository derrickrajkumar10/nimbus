"""Where the API publishes events: EventBridge, mapped as contracts/README.md specifies.

detail-type = event.type, source = "nimbus.<source>", detail = the whole event. Agent rules match
`source` with the prefix "nimbus.", so an event the API emits must be sent this way.
"""

import os
from typing import Any, Protocol

from nimbus_contracts.events import EVENT_TYPES

BUS_NAME_ENV = "NIMBUS_EVENT_BUS"


class PublishError(RuntimeError):
    pass


class Bus(Protocol):
    def publish(self, event: Any) -> None: ...


class MemoryBus:
    def __init__(self) -> None:
        self.events: list[Any] = []

    def publish(self, event: Any) -> None:
        self.events.append(event)


class EventBridgePublisher:
    """`client` is a boto3 "events" client; tests pass a fake."""

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

    def publish(self, event: Any) -> None:
        if not isinstance(event, tuple(EVENT_TYPES)):
            raise TypeError(f"only nimbus_contracts events can be published, got {type(event).__name__}")
        response = self.client.put_events(Entries=[self.entry(event)])
        if response.get("FailedEntryCount", 0):
            failed = response["Entries"][0]
            raise PublishError(f"EventBridge rejected {event.type}: {failed.get('ErrorCode')} {failed.get('ErrorMessage')}")
