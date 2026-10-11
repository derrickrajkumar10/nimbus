"""PlaceIndex seeding for a Replay Run (#14): who the Herald alerts when a Segment changes.

A Replay indexes only the devices subscribed to it (contracts/storage.md), so live
users never get Replay alerts. For the Michaung demo that's:

- the demo phones, on two Velachery Main Road Segments, with their real app device IDs;
- 150 simulated Subscribers on one Segment, more than Cedar's 100-recipient limit,
  so an alert there becomes a Ward Alert Proposal that waits for an officer.

Simulated rows use device IDs `sim-001` to `sim-150` and carry `simulated = true`.
Keys are deterministic, so seeding a Run twice writes the same rows.
"""

import os
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from dynamo import SeedError, batch_put  # noqa: F401  (SeedError: callers catch place_index.SeedError)

PK = "run_id#segment_id"
SK = "device_id#place_id"
TABLE_PARAM = "/nimbus/tables/PlaceIndex"
TABLE_ENV = "NIMBUS_TABLE_PLACEINDEX"  # the agents' override, if set

DEMO_SEGMENTS = ("27480309-1", "27480309-4")  # Velachery Main Road: flooded and likely in the fixture scene
CROWD_SEGMENT = "27320162-0"
CROWD_SIZE = 150
CROWD_PLACE = "sim-place"


@dataclass(frozen=True)
class Row:
    run_id: str
    segment_id: str
    device_id: str
    place_id: str
    simulated: bool

    def item(self) -> dict[str, Any]:
        return {
            PK: {"S": f"{self.run_id}#{self.segment_id}"},
            SK: {"S": f"{self.device_id}#{self.place_id}"},
            "simulated": {"BOOL": self.simulated},
        }


def parse_phone(value: str) -> tuple[str, str]:
    """`DEVICE_ID#PLACE_ID` as typed on the command line. The Herald splits at the first '#'."""
    device_id, _, place_id = value.partition("#")
    if not device_id or not place_id:
        raise ValueError(f"expected DEVICE_ID#PLACE_ID, got {value!r}")
    if device_id.startswith("sim-"):
        raise ValueError(f"{device_id!r}: 'sim-' device IDs are reserved for simulated Subscribers")
    return device_id, place_id


def demo_rows(run_id: str, phones: Sequence[tuple[str, str]]) -> list[Row]:
    return [Row(run_id, segment, device, place, False) for device, place in phones for segment in DEMO_SEGMENTS]


def crowd_rows(run_id: str, size: int = CROWD_SIZE) -> list[Row]:
    return [Row(run_id, CROWD_SEGMENT, f"sim-{n:03d}", CROWD_PLACE, True) for n in range(1, size + 1)]


def table_name(ssm: Callable[[], Any]) -> str:
    """The env override if set, else the SSM parameter. `ssm` makes the client, only when it's needed."""
    return os.environ.get(TABLE_ENV) or ssm().get_parameter(Name=TABLE_PARAM)["Parameter"]["Value"]


def write(
    client: Any,
    table: str,
    rows: Sequence[Row],
    *,
    max_retries: int = 5,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    batch_put(client, table, [row.item() for row in rows], what="PlaceIndex rows", max_retries=max_retries, sleep=sleep)
