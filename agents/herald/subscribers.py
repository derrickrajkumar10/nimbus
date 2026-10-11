"""Who to alert: the PlaceIndex lookup (contracts/storage.md), keyed by Run and Segment.

MemorySubscribers stands in for the PlaceIndex table until it's wired up (#32
asks who writes it). `practice_subscribers` are demo devices for the Michaung
Replay, on fixture Segments, labelled as such.
"""

from dataclasses import dataclass
from typing import Protocol


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


def practice_subscribers() -> MemorySubscribers:
    """Three demo phones subscribed to the Michaung Replay, with Saved Places on fixture Segments."""
    subs = MemorySubscribers()
    run = "replay-michaung"
    subs.add(run, "27480309-1", Subscriber("demo-phone-1", "place-home"))  # Velachery Main Road, flooded
    subs.add(run, "27480309-1", Subscriber("demo-phone-2", "place-bike-parking"))
    subs.add(run, "27480309-4", Subscriber("demo-phone-3", "place-office"))  # Velachery Main Road, likely
    return subs
