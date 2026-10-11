"""The FCM sender: who gets which language, what a stale token costs, and the shape agents rely on."""

import json
from types import SimpleNamespace

import pytest
from botocore.exceptions import ClientError
from pydantic import ValidationError

from push.core import Delivery, DynamoDevices, FirebaseMessenger, PushRequest, send_push

D1, D2, D3, D4 = "device-one-1", "device-two-2", "device-three-3", "device-four-4"


def request(**overrides):
    body = {
        "run_id": "replay-michaung",
        "device_ids": [D1, D2],
        "title": {"en": "Waterlogging likely", "ta": "நீர் தேங்க வாய்ப்பு"},
        "body": {"en": "Move your bike now", "ta": "வண்டியை நகர்த்துங்கள்"},
        "data": {"place_id": "home"},
    }
    return PushRequest.model_validate(body | overrides)


class MemoryDevices:
    def __init__(self, rows):
        self.rows, self.removed = dict(rows), []
        self.lookups = []

    def get_many(self, device_ids):
        self.lookups.append(list(device_ids))
        return {d: self.rows[d] for d in device_ids if d in self.rows}

    def remove_token(self, device_id, token):
        if self.rows.get(device_id, {}).get("fcm_token") != token:
            return False
        self.removed.append(device_id)
        del self.rows[device_id]
        return True


class FakeMessenger:
    def __init__(self, outcomes=None):
        self.outcomes, self.sent = outcomes or {}, []

    def send_each(self, messages):
        self.sent.extend(messages)
        return [self.outcomes.get(m.device_id, Delivery(ok=True)) for m in messages]


def row(token, language="en"):
    return {"fcm_token": token, "language": language}


# --- delivery --------------------------------------------------------------


def test_each_device_gets_its_own_language():
    devices = MemoryDevices({D1: row("tok-1", "ta"), D2: row("tok-2", "en")})
    messenger = FakeMessenger()
    assert send_push(request(), devices, messenger) == {"sent": 2, "failed": 0, "removed_tokens": 0}
    by_device = {m.device_id: m for m in messenger.sent}
    assert by_device[D1].title == "நீர் தேங்க வாய்ப்பு" and by_device[D1].body == "வண்டியை நகர்த்துங்கள்"
    assert by_device[D2].title == "Waterlogging likely"
    assert by_device[D1].token == "tok-1" and by_device[D1].data == {"place_id": "home"}


def test_an_unknown_language_falls_back_to_english():
    messenger = FakeMessenger()
    send_push(request(device_ids=[D1]), MemoryDevices({D1: row("tok", "fr")}), messenger)
    assert messenger.sent[0].title == "Waterlogging likely"


def test_unregistered_devices_count_as_failed_and_are_not_sent():
    messenger = FakeMessenger()
    result = send_push(request(), MemoryDevices({D1: row("tok-1")}), messenger)
    assert result == {"sent": 1, "failed": 1, "removed_tokens": 0}
    assert [m.device_id for m in messenger.sent] == [D1]


def test_a_stale_token_is_removed_and_counted():
    devices = MemoryDevices({D1: row("tok-1"), D2: row("tok-2")})
    messenger = FakeMessenger({D2: Delivery(ok=False, stale_token=True, error="Requested entity was not found")})
    assert send_push(request(), devices, messenger) == {"sent": 1, "failed": 1, "removed_tokens": 1}
    assert devices.removed == [D2] and D1 in devices.rows


def test_other_failures_never_delete_a_token():
    devices = MemoryDevices({D1: row("tok-1")})
    messenger = FakeMessenger({D1: Delivery(ok=False, stale_token=False, error="quota exceeded")})
    assert send_push(request(device_ids=[D1]), devices, messenger) == {"sent": 0, "failed": 1, "removed_tokens": 0}
    assert devices.removed == []


def test_a_refreshed_token_is_not_removed():
    # FCM said the old token is stale, but the app registered a new one in the meantime.
    class Refreshed(MemoryDevices):
        def remove_token(self, device_id, token):
            self.rows[device_id] = row("tok-new")
            return super().remove_token(device_id, token)

    devices = Refreshed({D1: row("tok-old")})
    messenger = FakeMessenger({D1: Delivery(ok=False, stale_token=True)})
    assert send_push(request(device_ids=[D1]), devices, messenger)["removed_tokens"] == 0
    assert devices.rows[D1]["fcm_token"] == "tok-new"


def test_devices_are_looked_up_in_batches_of_100_and_sent_in_batches_of_500():
    ids = [f"device-{i:04d}" for i in range(1000)]
    devices = MemoryDevices({d: row(f"tok-{d}") for d in ids})
    batches = []

    class Counting(FakeMessenger):
        def send_each(self, messages):
            batches.append(len(messages))
            return super().send_each(messages)

    result = send_push(request(device_ids=ids), devices, Counting())
    assert result == {"sent": 1000, "failed": 0, "removed_tokens": 0}
    assert [len(b) for b in devices.lookups] == [100] * 10 and batches == [500, 500]


# --- the request -----------------------------------------------------------


def test_the_request_matches_what_the_agents_push_client_sends():
    # agents/common/push.py Push.payload() produces exactly this shape.
    payload = {
        "run_id": "live",
        "device_ids": ["demo-phone-1"],
        "title": {"en": "a", "ta": "b"},
        "body": {"en": "c", "ta": "d"},
        "data": {"segment_id": "27480309-1"},
    }
    assert PushRequest.model_validate(payload).model_dump() == payload


@pytest.mark.parametrize(
    "overrides",
    [
        {"title": {"en": "only English"}},
        {"body": {"en": "x", "ta": "  "}},
        {"device_ids": []},
        {"device_ids": ["bad id"]},
        {"run_id": "michaung"},
        {"data": {"n": 1}},
        {"extra": True},
    ],
)
def test_malformed_requests_raise(overrides):
    with pytest.raises(ValidationError):
        request(**overrides)


def test_duplicate_devices_get_one_push():
    messenger = FakeMessenger()
    send_push(request(device_ids=[D1, D1, D1]), MemoryDevices({D1: row("tok")}), messenger)
    assert len(messenger.sent) == 1


# --- the Firebase adapter and the Devices table ----------------------------


class Unregistered(Exception):
    pass


class SenderMismatch(Exception):
    pass


def fake_sdk(results):
    calls = []

    def send_each(messages):
        calls.append(messages)
        return SimpleNamespace(responses=results)

    sdk = SimpleNamespace(
        Message=lambda **kw: SimpleNamespace(**kw),
        Notification=lambda **kw: SimpleNamespace(**kw),
        AndroidConfig=lambda **kw: SimpleNamespace(**kw),
        send_each=send_each,
        UnregisteredError=Unregistered,
        SenderIdMismatchError=SenderMismatch,
    )
    return sdk, calls


def test_the_firebase_adapter_builds_high_priority_messages_and_classifies_errors():
    results = [
        SimpleNamespace(success=True, exception=None),
        SimpleNamespace(success=False, exception=Unregistered("gone")),
        SimpleNamespace(success=False, exception=SenderMismatch("other project")),
        SimpleNamespace(success=False, exception=RuntimeError("quota")),
    ]
    sdk, calls = fake_sdk(results)
    from push.core import Outgoing

    messages = [Outgoing(f"device-{i}-xxxx", f"tok-{i}", "t", "b", {"k": "v"}) for i in range(4)]
    out = FirebaseMessenger(messaging=sdk).send_each(messages)
    assert [(d.ok, d.stale_token) for d in out] == [(True, False), (False, True), (False, True), (False, False)]
    first = calls[0][0]
    assert first.token == "tok-0" and first.notification.title == "t" and first.data == {"k": "v"}
    assert first.android.priority == "high"


class FakeDynamo:
    def __init__(self, pages=None, fail=None):
        self.pages, self.fail, self.deleted, self.requests = pages or [], fail, [], []

    def batch_get_item(self, RequestItems):  # noqa: N803 (boto3's name)
        self.requests.append(RequestItems)
        return self.pages.pop(0)

    def Table(self, name):  # noqa: N802
        outer = self

        class T:
            def delete_item(self, **kw):
                if outer.fail:
                    raise ClientError({"Error": {"Code": outer.fail, "Message": "x"}}, "DeleteItem")
                outer.deleted.append(kw)

        return T()


def test_dynamo_devices_follow_unprocessed_keys():
    table = "nimbus-Devices"
    resource = FakeDynamo(
        [
            {"Responses": {table: [{"device_id": D1, "fcm_token": "a"}]}, "UnprocessedKeys": {table: {"Keys": [{"device_id": D2}]}}},
            {"Responses": {table: [{"device_id": D2, "fcm_token": "b"}]}},
        ]
    )
    found = DynamoDevices(table, resource).get_many([D1, D2])
    assert set(found) == {D1, D2} and len(resource.requests) == 2
    assert resource.requests[0][table]["Keys"] == [{"device_id": D1}, {"device_id": D2}]


def test_dynamo_devices_remove_only_a_matching_token():
    resource = FakeDynamo()
    assert DynamoDevices("nimbus-Devices", resource).remove_token(D1, "tok") is True
    assert resource.deleted[0]["Key"] == {"device_id": D1} and "ConditionExpression" in resource.deleted[0]
    assert DynamoDevices("nimbus-Devices", FakeDynamo(fail="ConditionalCheckFailedException")).remove_token(D1, "tok") is False
    with pytest.raises(ClientError):
        DynamoDevices("nimbus-Devices", FakeDynamo(fail="ProvisionedThroughputExceededException")).remove_token(D1, "tok")


def test_the_lambda_returns_exactly_the_three_counts(monkeypatch):
    import push.handler as h

    devices = MemoryDevices({D1: row("tok")})
    monkeypatch.setattr(h, "DynamoDevices", lambda: devices)
    monkeypatch.setattr(h, "_messenger", lambda: FakeMessenger())
    result = h.handler(json.loads(request(device_ids=[D1]).model_dump_json()))
    assert result == {"sent": 1, "failed": 0, "removed_tokens": 0}
    with pytest.raises(ValidationError):
        h.handler({"run_id": "live"})
