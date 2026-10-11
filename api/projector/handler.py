"""Projector Lambda: an EventBridge rule on the `nimbus` bus sends it every projected event.

Errors are raised on purpose: Lambda retries, and the rule's dead-letter queue keeps
what still fails, so no event is silently dropped.
"""

from typing import Any

from projector.core import DynamoStore, Store, process

_store: Store | None = None


def handler(payload: dict[str, Any], lambda_context: Any = None) -> int:
    global _store
    if _store is None:
        _store = DynamoStore()  # reused while the Lambda stays warm
    return process(payload, _store)
