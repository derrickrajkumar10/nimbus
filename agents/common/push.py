"""Hand alerts to Varun's FCM sender (#6), the way common/bus.py hands events to the bus.

The sender is a Lambda whose name comes from SSM /nimbus/lambdas/send-push, set
on agent Lambdas as NIMBUS_SEND_PUSH_FUNCTION. Its input is a Push payload and it
returns {"sent", "failed", "removed_tokens"}. Partly failed delivery (stale
tokens) is a normal result. Only a crashed or malformed invocation raises.
The Herald adds the [REPLAY] prefix; the sender sends text as given.
"""

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

SEND_PUSH_ENV = "NIMBUS_SEND_PUSH_FUNCTION"
LANGUAGES = ("en", "ta")
_RUN_ID = re.compile(r"^(live|replay-[a-z0-9-]+)$")


@dataclass(frozen=True)
class Push:
    run_id: str
    device_ids: tuple[str, ...]
    title: dict[str, str]
    body: dict[str, str]
    data: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _RUN_ID.match(self.run_id):
            raise ValueError(f"not a run_id: {self.run_id!r}")
        if not self.device_ids:
            raise ValueError("a push needs at least one device")
        for part, texts in (("title", self.title), ("body", self.body)):
            missing = [lang for lang in LANGUAGES if not (texts.get(lang) or "").strip()]
            if missing:
                raise ValueError(f"push {part} is missing {', '.join(missing)}: alerts go out in English and Tamil")
        if not all(isinstance(v, str) for v in self.data.values()):
            raise ValueError("push data values must be strings (FCM data payloads are string maps)")

    def payload(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "device_ids": list(self.device_ids),
            "title": {lang: self.title[lang] for lang in LANGUAGES},
            "body": {lang: self.body[lang] for lang in LANGUAGES},
            "data": dict(self.data),
        }


@dataclass(frozen=True)
class PushResult:
    sent: int
    failed: int
    removed_tokens: int


class PushError(RuntimeError):
    pass


class PushSender(Protocol):
    def send(self, push: Push) -> PushResult: ...


class RecordOnlySender:
    """No push sender configured (#6 not deployed): nothing reaches a phone.

    The Herald still records the alert (alert.sent, activity) and says "push not connected".
    """

    connected = False

    def send(self, push: Push) -> PushResult:
        return PushResult(sent=0, failed=0, removed_tokens=0)


class MemoryPushSender:
    """A fake sender: pushes are recorded in `sent` instead of reaching phones."""

    connected = True

    def __init__(self) -> None:
        self.sent: list[Push] = []

    def send(self, push: Push) -> PushResult:
        self.sent.append(push)
        return PushResult(sent=len(push.device_ids), failed=0, removed_tokens=0)


class LambdaPushSender:
    """Invokes the send-push Lambda synchronously. `client` is a boto3 "lambda" client."""

    connected = True

    def __init__(self, function_name: str | None = None, client: Any = None) -> None:
        self.function_name = function_name or os.environ.get(SEND_PUSH_ENV)
        if not self.function_name:
            raise ValueError(f"no send-push Lambda: pass function_name or set {SEND_PUSH_ENV}")
        self._client = client

    @property
    def client(self) -> Any:
        if self._client is None:
            import boto3

            self._client = boto3.client("lambda")
        return self._client

    def send(self, push: Push) -> PushResult:
        response = self.client.invoke(
            FunctionName=self.function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(push.payload()).encode(),
        )
        raw = response["Payload"].read()
        # A Lambda that raises still returns 200; the failure is only in FunctionError.
        if response.get("FunctionError"):
            raise PushError(f"send-push failed ({response['FunctionError']}): {raw.decode(errors='replace')[:500]}")
        try:
            result = json.loads(raw)
            return PushResult(sent=int(result["sent"]), failed=int(result["failed"]), removed_tokens=int(result["removed_tokens"]))
        except (ValueError, KeyError, TypeError) as exc:
            raise PushError(f"send-push returned an unexpected response: {raw.decode(errors='replace')[:500]}") from exc
