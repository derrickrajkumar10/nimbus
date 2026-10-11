"""Console API Lambda behind the API Gateway HTTP API.

Publish failures after a decision was saved come back as 502 with a body that says the retry is safe.
"""

from functools import cache
from typing import Any

from console.bus import EventBridgePublisher, PublishError
from console.http import respond
from console.routes import Console
from console.store import DynamoStore


@cache
def _console() -> Console:
    return Console(DynamoStore(), EventBridgePublisher())  # built once, reused while warm


def handler(event: dict[str, Any], lambda_context: Any = None) -> dict[str, Any]:
    try:
        return _console().handle(event)
    except PublishError as error:
        return respond(
            502,
            {"error": "event_not_sent", "message": f"the decision was saved but its event was not sent; retry the same request ({error})"},
        )
