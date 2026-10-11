"""Record IDs: a short prefix plus a ULID, so sorting by ID gives creation order (contracts/storage.md).

The timestamp part comes from the caller's time, normally the event's sim_time,
so IDs sort in storm order within a Replay.
"""

import secrets
from datetime import datetime

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def ulid(at: datetime) -> str:
    """A 26-character ULID: 48-bit millisecond timestamp, then 80 random bits."""
    value = (int(at.timestamp() * 1000) << 80) | secrets.randbits(80)
    return "".join(_CROCKFORD[(value >> shift) & 31] for shift in range(125, -1, -5))


def new_id(prefix: str, at: datetime) -> str:
    return f"{prefix}-{ulid(at)}"
