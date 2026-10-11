"""A very small router for API Gateway HTTP API (payload format 2.0) events.

Routes are matched on method and path. A handler gets a `Request` and returns a
JSON-able body, or raises `HttpError` for a client or upstream failure.
"""

import base64
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


class HttpError(Exception):
    def __init__(self, status: int, code: str, message: str, **extra: Any) -> None:
        super().__init__(message)
        self.status, self.code, self.message, self.extra = status, code, message, extra


@dataclass(frozen=True)
class Request:
    method: str
    path: str
    query: dict[str, str] = field(default_factory=dict)
    params: dict[str, str] = field(default_factory=dict)
    raw_body: str = ""

    def json(self) -> Any:
        try:
            return json.loads(self.raw_body or "null")
        except ValueError as error:
            raise HttpError(400, "invalid_json", "the request body is not valid JSON") from error


Handler = Callable[[Request], Any]


def _pattern(path: str) -> re.Pattern[str]:
    return re.compile("^" + re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", path) + "$")


class Router:
    def __init__(self) -> None:
        self._routes: list[tuple[str, str, re.Pattern[str], Handler]] = []

    def add(self, method: str, path: str, handler: Handler) -> None:
        self._routes.append((method, path, _pattern(path), handler))

    @property
    def table(self) -> list[tuple[str, str]]:
        """(method, path) for every route, so the API stack can expose exactly these."""
        return [(method, path) for method, path, _, _ in self._routes]

    def handle(self, event: dict[str, Any]) -> dict[str, Any]:
        http = event.get("requestContext", {}).get("http", {})
        method, path = http.get("method", "GET").upper(), event.get("rawPath", "/")
        body = event.get("body") or ""
        if event.get("isBase64Encoded"):
            body = base64.b64decode(body).decode()
        query = {k: v for k, v in (event.get("queryStringParameters") or {}).items() if v is not None}
        try:
            return self._dispatch(method, path, query, body)
        except HttpError as error:
            return respond(error.status, {"error": error.code, "message": error.message, **error.extra})

    def _dispatch(self, method: str, path: str, query: dict[str, str], body: str) -> dict[str, Any]:
        path_matched = False
        for route_method, _, pattern, handler in self._routes:
            match = pattern.match(path)
            if not match:
                continue
            path_matched = True
            if route_method == method:
                request = Request(method, path, query, match.groupdict(), body)
                return respond(200, handler(request))
        if path_matched:
            raise HttpError(405, "method_not_allowed", f"{method} is not allowed on {path}")
        raise HttpError(404, "not_found", f"no route for {path}")


def respond(status: int, body: Any) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }
