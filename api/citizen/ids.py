"""Record ids: a short prefix plus a ULID, so sorting by id gives creation order (contracts/storage.md)."""

import secrets
from datetime import datetime

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
ULID_CHARS = "0-9A-HJKMNP-TV-Z"  # Crockford's base32, for patterns


def new_id(prefix: str, at: datetime) -> str:
    """e.g. rp-01HZX3... The timestamp is `at`, so ids sort in the order the Run saw them."""
    value = (int(at.timestamp() * 1000) << 80) | secrets.randbits(80)
    return f"{prefix}-" + "".join(_CROCKFORD[(value >> shift) & 31] for shift in range(125, -1, -5))
