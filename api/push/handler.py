"""send-push Lambda, named `nimbus-send-push`. Invoked synchronously by the Herald.

A malformed request raises, so the caller sees a FunctionError instead of a quiet partial send.
"""

from functools import cache
from typing import Any

from push.core import DynamoDevices, FirebaseMessenger, PushRequest, send_push


@cache
def _messenger() -> FirebaseMessenger:
    return FirebaseMessenger()  # the Firebase app is created on first send, then reused while warm


def handler(event: dict[str, Any], lambda_context: Any = None) -> dict[str, int]:
    request = PushRequest.model_validate(event)
    return send_push(request, DynamoDevices(), _messenger())
