"""Seeding writes shared by place_index.py and resources.py."""

import time
from collections.abc import Callable, Sequence
from typing import Any

BATCH_LIMIT = 25  # BatchWriteItem's maximum


class SeedError(RuntimeError):
    pass


def batch_put(
    client: Any,
    table: str,
    items: Sequence[dict[str, Any]],
    *,
    what: str,
    max_retries: int = 5,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """BatchWriteItem in chunks of 25, retrying unprocessed items with backoff. `what` names the rows in errors."""
    for start in range(0, len(items), BATCH_LIMIT):
        requests = {table: [{"PutRequest": {"Item": item}} for item in items[start : start + BATCH_LIMIT]]}
        for attempt in range(max_retries + 1):
            if attempt:
                sleep(0.1 * 2**attempt)
            requests = client.batch_write_item(RequestItems=requests).get("UnprocessedItems") or {}
            if not requests:
                break
        else:
            raise SeedError(f"DynamoDB left {len(requests.get(table, []))} {what} unwritten in {table}")
