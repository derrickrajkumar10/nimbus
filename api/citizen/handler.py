"""Citizen API Lambda behind the API Gateway HTTP API."""

from functools import cache
from typing import Any

from citizen.routes import Citizen
from citizen.store import DynamoStore


@cache
def _citizen() -> Citizen:
    return Citizen(DynamoStore())  # built once, reused (with its Segments cache) while warm


def handler(event: dict[str, Any], lambda_context: Any = None) -> dict[str, Any]:
    return _citizen().handle(event)
