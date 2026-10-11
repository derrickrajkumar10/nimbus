"""The Pathfinder agent (#23), called synchronously for POST /routes.

Request and response are the contracts in nimbus_contracts.routes. The function name comes from
NIMBUS_PATHFINDER_FUNCTION; with none set, routing answers 503 and the app shows "no route service".
"""

import json
import os
from typing import Any, Protocol

FUNCTION_ENV = "NIMBUS_PATHFINDER_FUNCTION"


class RoutingUnavailable(Exception):
    """No Pathfinder to call (not configured, or not deployed yet)."""


class RoutingFailed(Exception):
    """The Pathfinder was called and failed."""


class Pathfinder(Protocol):
    def route(self, request: dict[str, Any]) -> dict[str, Any]: ...


class LambdaPathfinder:
    """`client` is a boto3 "lambda" client."""

    def __init__(self, function_name: str | None = None, client: Any = None) -> None:
        self.function_name = function_name or os.environ.get(FUNCTION_ENV)
        if not self.function_name:
            raise RoutingUnavailable(f"set {FUNCTION_ENV} to the Pathfinder Lambda's name")
        self._client = client

    @property
    def client(self) -> Any:
        if self._client is None:
            import boto3
            from botocore.config import Config

            # A person is waiting: give up quickly rather than retry.
            self._client = boto3.client("lambda", config=Config(read_timeout=12, retries={"max_attempts": 0}))
        return self._client

    def route(self, request: dict[str, Any]) -> dict[str, Any]:
        from botocore.exceptions import ClientError

        try:
            response = self.client.invoke(
                FunctionName=self.function_name, InvocationType="RequestResponse", Payload=json.dumps(request).encode()
            )
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") == "ResourceNotFoundException":
                raise RoutingUnavailable(f"Lambda {self.function_name} doesn't exist yet") from error
            raise RoutingFailed(str(error)) from error
        raw = response["Payload"].read()
        if response.get("FunctionError"):
            raise RoutingFailed(f"{self.function_name} failed: {raw.decode(errors='replace')[:300]}")
        try:
            return json.loads(raw)
        except ValueError as error:
            raise RoutingFailed("the Pathfinder returned something that isn't JSON") from error
