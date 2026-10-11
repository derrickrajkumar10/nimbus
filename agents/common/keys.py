"""DynamoDB key helpers.

Sort keys that hold a time sort as text (contracts/storage.md), so every such key
must be in UTC with a "Z" suffix and a fixed width. Pydantic's JSON drops the
fraction when it's zero ("07:00:00Z"), and "07:00:00.500000Z" sorts before it as
text although it's later, so never use an event's JSON time as a key directly.
"""

from datetime import UTC, datetime


def utc_key(dt: datetime) -> str:
    """`dt` as a fixed-width UTC sort key, e.g. 2023-12-03T20:30:00.000000Z."""
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"sort-key times must be timezone-aware, got naive {dt.isoformat()}")
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
