"""FCM push sender (#6): the Lambda the Herald calls to put an alert on a citizen's phone.

Input is the payload agents/common/push.py builds:
    {"run_id", "device_ids": [...], "title": {"en", "ta"}, "body": {"en", "ta"}, "data": {str: str}}
Output is exactly {"sent", "failed", "removed_tokens"}. A device whose token FCM says is stale is
removed from `Devices`, and only if the stored token is still that one (the app may have refreshed it).
The text is sent as given: the Herald adds the [REPLAY] prefix.
"""

import json
import logging
import re
from dataclasses import dataclass
from typing import Annotated, Any, Protocol

from nimbus_contracts.common import RunId
from pydantic import BaseModel, ConfigDict, Field, field_validator

log = logging.getLogger(__name__)

LANGUAGES = ("en", "ta")
FCM_BATCH_LIMIT = 500  # messaging.send_each accepts up to 500 messages
DEVICE_BATCH_LIMIT = 100  # BatchGetItem accepts up to 100 keys
DEVICE_ID = re.compile(r"^[A-Za-z0-9:_-]{8,80}$")  # same rule as the citizen API's X-Install-Id
SECRET_ENV = "NIMBUS_FIREBASE_SECRET"
DEFAULT_SECRET = "nimbus/firebase"


class PushRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: RunId
    device_ids: Annotated[list[str], Field(min_length=1, max_length=1000)]
    title: dict[str, str]
    body: dict[str, str]
    data: dict[str, str] = {}

    @field_validator("device_ids")
    @classmethod
    def _device_ids(cls, ids: list[str]) -> list[str]:
        bad = [i for i in ids if not DEVICE_ID.match(i)]
        if bad:
            raise ValueError(f"not device ids: {bad[:3]}")
        return list(dict.fromkeys(ids))  # one push per device

    @field_validator("title", "body")
    @classmethod
    def _both_languages(cls, texts: dict[str, str]) -> dict[str, str]:
        missing = [lang for lang in LANGUAGES if not (texts.get(lang) or "").strip()]
        if missing:
            raise ValueError(f"missing {', '.join(missing)}: alerts go out in English and Tamil")
        return {lang: texts[lang] for lang in LANGUAGES}


@dataclass(frozen=True)
class Outgoing:
    device_id: str
    token: str
    title: str
    body: str
    data: dict[str, str]


@dataclass(frozen=True)
class Delivery:
    ok: bool
    stale_token: bool = False  # FCM says this token is no longer registered
    error: str | None = None


class Devices(Protocol):
    def get_many(self, device_ids: list[str]) -> dict[str, dict[str, Any]]:
        """`Devices` rows by device id. Unknown ids are missing from the result."""
        ...

    def remove_token(self, device_id: str, token: str) -> bool:
        """Delete the device's row if it still holds `token`. False when it had changed or was gone."""
        ...


class Messenger(Protocol):
    def send_each(self, messages: list[Outgoing]) -> list[Delivery]: ...


def send_push(request: PushRequest, devices: Devices, messenger: Messenger) -> dict[str, int]:
    rows: dict[str, dict[str, Any]] = {}
    for start in range(0, len(request.device_ids), DEVICE_BATCH_LIMIT):
        rows |= devices.get_many(request.device_ids[start : start + DEVICE_BATCH_LIMIT])

    outgoing, failed = [], 0
    for device_id in request.device_ids:
        row = rows.get(device_id)
        if not row or not row.get("fcm_token"):
            failed += 1  # never registered, or removed after a stale token
            continue
        lang = row.get("language") if row.get("language") in LANGUAGES else "en"
        outgoing.append(Outgoing(device_id, row["fcm_token"], request.title[lang], request.body[lang], dict(request.data)))

    sent = removed = 0
    for start in range(0, len(outgoing), FCM_BATCH_LIMIT):
        batch = outgoing[start : start + FCM_BATCH_LIMIT]
        for message, delivery in zip(batch, messenger.send_each(batch), strict=True):
            if delivery.ok:
                sent += 1
                continue
            failed += 1
            if delivery.stale_token and devices.remove_token(message.device_id, message.token):
                removed += 1
            elif not delivery.stale_token:
                log.warning("push to %s failed: %s", message.device_id, delivery.error)
    return {"sent": sent, "failed": failed, "removed_tokens": removed}


class DynamoDevices:
    """`resource` is a boto3 dynamodb resource; the table name comes from NIMBUS_TABLE_DEVICES."""

    def __init__(self, table_name: str | None = None, resource: Any = None) -> None:
        import os

        self.table_name = table_name or os.environ["NIMBUS_TABLE_DEVICES"]
        self._resource = resource

    @property
    def resource(self) -> Any:
        if self._resource is None:
            import boto3

            self._resource = boto3.resource("dynamodb")
        return self._resource

    def get_many(self, device_ids):
        request = {self.table_name: {"Keys": [{"device_id": d} for d in device_ids]}}
        found: dict[str, dict[str, Any]] = {}
        while request:
            response = self.resource.batch_get_item(RequestItems=request)
            for item in response.get("Responses", {}).get(self.table_name, []):
                found[item["device_id"]] = item
            request = response.get("UnprocessedKeys") or {}
        return found

    def remove_token(self, device_id, token):
        from boto3.dynamodb.conditions import Attr
        from botocore.exceptions import ClientError

        try:
            self.resource.Table(self.table_name).delete_item(
                Key={"device_id": device_id}, ConditionExpression=Attr("fcm_token").eq(token)
            )
            return True
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                return False
            raise


class FirebaseMessenger:
    """Sends through the Firebase Admin SDK. `messaging` is injectable for tests.

    The service-account JSON comes from Secrets Manager (`nimbus/firebase`) and is read on first use.
    """

    def __init__(self, secret_id: str | None = None, secrets_client: Any = None, messaging: Any = None) -> None:
        import os

        self.secret_id = secret_id or os.environ.get(SECRET_ENV, DEFAULT_SECRET)
        self._secrets, self._messaging = secrets_client, messaging

    def _sdk(self) -> Any:
        if self._messaging is None:
            import boto3
            import firebase_admin
            from firebase_admin import credentials, messaging

            client = self._secrets or boto3.client("secretsmanager")
            account = json.loads(client.get_secret_value(SecretId=self.secret_id)["SecretString"])
            if not firebase_admin._apps:
                firebase_admin.initialize_app(credentials.Certificate(account))
            self._messaging = messaging
        return self._messaging

    def send_each(self, messages: list[Outgoing]) -> list[Delivery]:
        sdk = self._sdk()
        built = [
            sdk.Message(
                token=m.token,
                notification=sdk.Notification(title=m.title, body=m.body),
                data=m.data,
                android=sdk.AndroidConfig(priority="high"),  # a flood alert shouldn't wait for the phone to wake
            )
            for m in messages
        ]
        out = []
        for response in sdk.send_each(built).responses:
            if response.success:
                out.append(Delivery(ok=True))
            else:
                stale = isinstance(response.exception, (sdk.UnregisteredError, sdk.SenderIdMismatchError))
                out.append(Delivery(ok=False, stale_token=stale, error=str(response.exception)))
        return out
