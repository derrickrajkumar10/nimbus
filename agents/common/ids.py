"""Record IDs: a short prefix plus a ULID, so sorting by ID gives creation order (contracts/storage.md).

The timestamp part comes from the caller's time, normally the event's sim_time,
so IDs sort in storm order within a Replay.
"""

import hashlib
import secrets
from datetime import datetime

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def ulid(at: datetime, seed: str | None = None) -> str:
    """A 26-character ULID: 48-bit millisecond timestamp, then 80 bits.

    With a `seed` the 80 bits come from its hash, so the same seed gives the same ID.
    Agents seed from the triggering event, so a retried delivery reproduces its IDs (#42).
    """
    tail = int.from_bytes(hashlib.sha256(seed.encode()).digest()[:10]) if seed is not None else secrets.randbits(80)
    value = (int(at.timestamp() * 1000) << 80) | tail
    return "".join(_CROCKFORD[(value >> shift) & 31] for shift in range(125, -1, -5))


def new_id(prefix: str, at: datetime, seed: str | None = None) -> str:
    return f"{prefix}-{ulid(at, seed)}"
