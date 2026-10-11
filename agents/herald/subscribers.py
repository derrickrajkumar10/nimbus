"""Who to alert: the PlaceIndex lookup (contracts/storage.md), keyed by Run and Segment.

PlaceIndex is written by the API (PUT /saved-places) and, for a Replay's demo
devices, by the Replay Driver (#32). DynamoSubscribers reads it; MemorySubscribers
and `practice_subscribers` (demo devices on fixture Segments) are for local runs.
"""

from dataclasses import dataclass
from typing import Any, Protocol

from common.dynamo import dynamo_client, from_item, query_all, table_name

PK = "run_id#segment_id"
SK = "device_id#place_id"


@dataclass(frozen=True)
class Subscriber:
    device_id: str
    place_id: str


class Subscribers(Protocol):
    def for_segment(self, run_id: str, segment_id: str) -> list[Subscriber]: ...
    def all_in_run(self, run_id: str) -> list[Subscriber]: ...


class MemorySubscribers:
    def __init__(self, index: dict[tuple[str, str], list[Subscriber]] | None = None) -> None:
        self._index = index or {}

    def add(self, run_id: str, segment_id: str, subscriber: Subscriber) -> None:
        self._index.setdefault((run_id, segment_id), []).append(subscriber)

    def for_segment(self, run_id: str, segment_id: str) -> list[Subscriber]:
        return list(self._index.get((run_id, segment_id), []))

    def all_in_run(self, run_id: str) -> list[Subscriber]:
        seen: dict[str, Subscriber] = {}
        for (run, _), subs in self._index.items():
            if run == run_id:
                for sub in subs:
                    seen.setdefault(sub.device_id + "#" + sub.place_id, sub)
        return list(seen.values())


class DynamoSubscribers:
    """PlaceIndex rows: `run_id#segment_id` = "live#27320162-0", `device_id#place_id` = "dev-1#place-home"."""

    def __init__(self, table: str, client: Any = None) -> None:
        self.table = table
        self._client = client

    @classmethod
    def from_env(cls) -> "DynamoSubscribers | None":
        name = table_name("PlaceIndex")
        return cls(name) if name else None

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = dynamo_client()
        return self._client

    @staticmethod
    def _subscriber(item: dict) -> Subscriber:
        device_id, _, place_id = from_item(item)[SK].partition("#")
        return Subscriber(device_id, place_id)

    def for_segment(self, run_id: str, segment_id: str) -> list[Subscriber]:
        items = query_all(
            self.client,
            TableName=self.table,
            KeyConditionExpression="#pk = :pk",
            ExpressionAttributeNames={"#pk": PK},
            ExpressionAttributeValues={":pk": {"S": f"{run_id}#{segment_id}"}},
        )
        return [self._subscriber(item) for item in items]

    def all_in_run(self, run_id: str) -> list[Subscriber]:
        # Ward Alerts only, after an officer approves: a filtered Scan is fine at ward scale.
        seen: dict[str, Subscriber] = {}
        kwargs: dict = {
            "TableName": self.table,
            "FilterExpression": "begins_with(#pk, :run)",
            "ExpressionAttributeNames": {"#pk": PK},
            "ExpressionAttributeValues": {":run": {"S": f"{run_id}#"}},
        }
        while True:
            page = self.client.scan(**kwargs)
            for item in page.get("Items", []):
                sub = self._subscriber(item)
                seen.setdefault(f"{sub.device_id}#{sub.place_id}", sub)
            if "LastEvaluatedKey" not in page:
                return list(seen.values())
            kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]


def practice_subscribers() -> MemorySubscribers:
    """Three demo phones subscribed to the Michaung Replay, with Saved Places on fixture Segments."""
    subs = MemorySubscribers()
    run = "replay-michaung"
    subs.add(run, "27480309-1", Subscriber("demo-phone-1", "place-home"))  # Velachery Main Road, flooded
    subs.add(run, "27480309-1", Subscriber("demo-phone-2", "place-bike-parking"))
    subs.add(run, "27480309-4", Subscriber("demo-phone-3", "place-office"))  # Velachery Main Road, likely
    return subs
