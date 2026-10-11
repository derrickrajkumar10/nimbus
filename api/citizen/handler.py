"""Citizen API Lambda behind the API Gateway HTTP API."""

from functools import cache
from typing import Any

from citizen.pathfinder import LambdaPathfinder, RoutingUnavailable
from citizen.photos import S3Photos
from citizen.routes import Citizen
from citizen.store import DynamoStore
from console.bus import EventBridgePublisher


@cache
def _citizen() -> Citizen:
    try:
        router = LambdaPathfinder()
    except RoutingUnavailable:
        router = None  # POST /routes answers 503 until the Pathfinder's name is set
    # Built once, reused (with its Segments cache) while warm.
    return Citizen(DynamoStore(), bus=EventBridgePublisher(), photos=S3Photos(), pathfinder=router)


def handler(event: dict[str, Any], lambda_context: Any = None) -> dict[str, Any]:
    return _citizen().handle(event)
