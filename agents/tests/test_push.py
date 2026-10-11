"""Push client against botocore's Stubber with fake keys: nothing reaches AWS or Firebase."""

import io
import json

import boto3
import pytest
from botocore.response import StreamingBody
from botocore.stub import Stubber

from common.push import SEND_PUSH_ENV, LambdaPushSender, MemoryPushSender, Push, PushError, PushResult


def push(**overrides) -> Push:
    fields = {
        "run_id": "replay-michaung",
        "device_ids": ("dev-1", "dev-2"),
        "title": {"en": "[REPLAY] Flood alert", "ta": "[REPLAY] வெள்ள எச்சரிக்கை"},
        "body": {"en": "Move your two-wheeler now.", "ta": "உங்கள் இருசக்கர வாகனத்தை இப்போதே நகர்த்துங்கள்."},
        "data": {"segment_id": "27480309-1"},
    }
    fields.update(overrides)
    return Push(**fields)


def fake_lambda_client():
    return boto3.client("lambda", region_name="us-east-1", aws_access_key_id="fake", aws_secret_access_key="fake")


def stream(obj) -> StreamingBody:
    raw = json.dumps(obj).encode() if not isinstance(obj, bytes) else obj
    return StreamingBody(io.BytesIO(raw), len(raw))


def test_invokes_the_send_push_lambda_with_the_agreed_payload():
    client = fake_lambda_client()
    sender = LambdaPushSender("nimbus-send-push", client=client)
    p = push()
    expected = {
        "FunctionName": "nimbus-send-push",
        "InvocationType": "RequestResponse",
        "Payload": json.dumps(p.payload()).encode(),
    }
    with Stubber(client) as stub:
        stub.add_response("invoke", {"StatusCode": 200, "Payload": stream({"sent": 2, "failed": 0, "removed_tokens": 0})}, expected)
        result = sender.send(p)
        stub.assert_no_pending_responses()
    assert result == PushResult(sent=2, failed=0, removed_tokens=0)


def test_payload_shape_matches_the_sender_contract():
    payload = push().payload()
    assert set(payload) == {"run_id", "device_ids", "title", "body", "data"}
    assert set(payload["title"]) == set(payload["body"]) == {"en", "ta"}
    assert payload["device_ids"] == ["dev-1", "dev-2"]


def test_partial_delivery_is_a_result_not_an_error():
    client = fake_lambda_client()
    with Stubber(client) as stub:
        stub.add_response("invoke", {"StatusCode": 200, "Payload": stream({"sent": 1, "failed": 1, "removed_tokens": 1})})
        assert LambdaPushSender("f", client=client).send(push()) == PushResult(1, 1, 1)


def test_a_crashed_sender_raises_instead_of_passing_silently():
    client = fake_lambda_client()
    crash = {"errorMessage": "Firebase credentials missing", "errorType": "KeyError"}
    with Stubber(client) as stub:
        stub.add_response("invoke", {"StatusCode": 200, "FunctionError": "Unhandled", "Payload": stream(crash)})
        with pytest.raises(PushError, match="Firebase credentials missing"):
            LambdaPushSender("f", client=client).send(push())


def test_an_unexpected_response_raises():
    client = fake_lambda_client()
    with Stubber(client) as stub:
        stub.add_response("invoke", {"StatusCode": 200, "Payload": stream({"ok": True})})
        with pytest.raises(PushError, match="unexpected response"):
            LambdaPushSender("f", client=client).send(push())


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"title": {"en": "Flood alert"}}, "title is missing ta"),
        ({"body": {"en": "x", "ta": "  "}}, "body is missing ta"),
        ({"title": {"ta": "வெள்ள எச்சரிக்கை"}}, "title is missing en"),
        ({"device_ids": ()}, "at least one device"),
        ({"run_id": "michaung"}, "not a run_id"),
        ({"data": {"score": 92}}, "must be strings"),
    ],
)
def test_bad_pushes_are_rejected_before_any_call(overrides, message):
    with pytest.raises(ValueError, match=message):
        push(**overrides)


def test_function_name_comes_from_the_environment(monkeypatch):
    monkeypatch.setenv(SEND_PUSH_ENV, "nimbus-send-push-from-ssm")
    assert LambdaPushSender(client=fake_lambda_client()).function_name == "nimbus-send-push-from-ssm"


def test_missing_function_name_is_a_clear_error(monkeypatch):
    monkeypatch.delenv(SEND_PUSH_ENV, raising=False)
    with pytest.raises(ValueError, match=SEND_PUSH_ENV):
        LambdaPushSender(client=fake_lambda_client())


def test_memory_sender_records_pushes():
    sender = MemoryPushSender()
    assert sender.send(push()) == PushResult(sent=2, failed=0, removed_tokens=0)
    assert sender.sent == [push()]
