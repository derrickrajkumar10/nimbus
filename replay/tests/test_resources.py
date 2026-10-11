"""Resources seeding, against botocore's Stubber with fake keys, so nothing reaches AWS."""

from decimal import Decimal

import boto3
import pytest
from boto3.dynamodb.types import TypeDeserializer
from botocore.stub import Stubber
from nimbus_contracts.entities import Resource

import driver
import resources
from dynamo import SeedError


def fake_client(service: str):
    return boto3.client(service, region_name="us-east-1", aws_access_key_id="fake", aws_secret_access_key="fake")


def plain(item: dict) -> dict:
    return {k: TypeDeserializer().deserialize(v) for k, v in item.items()}


def test_fixture_resources_are_rewritten_to_the_run():
    run = resources.for_run("replay-michaung-2")

    assert [r.resource_id for r in run] == ["rs-pump-1", "rs-pump-2", "rs-tree-1"]
    assert {r.run_id for r in run} == {"replay-michaung-2"}
    assert next(r for r in run if r.resource_id == "rs-pump-2").status == "free"


def test_items_are_the_json_model_dump_keyed_by_run_and_resource():
    pump = next(r for r in resources.for_run("replay-michaung") if r.resource_id == "rs-pump-2")

    item = plain(resources.item(pump))

    assert item["run_id"] == "replay-michaung" and item["resource_id"] == "rs-pump-2"
    assert item["location"]["lat"] == Decimal("12.9775075")  # DynamoDB needs Decimal, not float
    assert Resource.model_validate({**item, "location": {k: float(v) for k, v in item["location"].items()}}) == pump
    assert set(item) == set(pump.model_dump(mode="json"))


def test_table_name_from_ssm_or_env(monkeypatch):
    monkeypatch.delenv(resources.TABLE_ENV, raising=False)
    ssm = fake_client("ssm")
    param = {"Parameter": {"Name": resources.TABLE_PARAM, "Type": "String", "Value": "nimbus-Resources"}}
    with Stubber(ssm) as stub:
        stub.add_response("get_parameter", param, {"Name": "/nimbus/tables/Resources"})
        assert resources.table_name(lambda: ssm) == "nimbus-Resources"

    monkeypatch.setenv(resources.TABLE_ENV, "override")
    assert resources.table_name(lambda: pytest.fail("SSM was asked")) == "override"


def test_write_puts_every_resource_in_one_batch():
    run = resources.for_run("replay-michaung")
    client = fake_client("dynamodb")
    expected = {"RequestItems": {"res": [{"PutRequest": {"Item": resources.item(r)}} for r in run]}}
    with Stubber(client) as stub:
        stub.add_response("batch_write_item", {"UnprocessedItems": {}}, expected)
        resources.write(client, "res", run)
        stub.assert_no_pending_responses()


def test_write_gives_up_on_rows_dynamodb_keeps_refusing():
    run = resources.for_run("replay-michaung")
    left = {"res": [{"PutRequest": {"Item": resources.item(run[0])}}]}
    client = fake_client("dynamodb")
    with Stubber(client) as stub:
        for _ in range(2):
            stub.add_response("batch_write_item", {"UnprocessedItems": left})
        with pytest.raises(SeedError, match="1 Resources unwritten in res"):
            resources.write(client, "res", run, max_retries=1, sleep=lambda _: None)


def test_no_seed_skips_resources_too(monkeypatch):
    events = fake_client("events")

    def clients(service):
        assert service == "events", f"--no-seed must not touch {service}"
        return events

    monkeypatch.setattr(driver, "_aws_client", clients)
    with Stubber(events) as stub:
        stub.add_response("put_events", {"FailedEntryCount": 0, "Entries": [{"EventId": "aws-1"}]})
        assert driver.main(["--ticks", "1", "--no-seed"]) == 0


def test_dry_run_reports_resources_without_aws(monkeypatch, capsys):
    monkeypatch.setattr(driver, "_aws_client", lambda service: pytest.fail(f"dry run created a {service} client"))

    assert driver.main(["--dry-run", "--ticks", "1", "--speed", "0"]) == 0

    assert "would put 5 Resources for Run replay-michaung" in capsys.readouterr().err


def test_a_replay_run_is_seeded_with_two_extra_free_pumps():
    run = resources.seeded("replay-michaung-2")

    assert [r.resource_id for r in run] == ["rs-pump-1", "rs-pump-2", "rs-tree-1", "rs-pump-3", "rs-pump-4"]
    assert {r.run_id for r in run} == {"replay-michaung-2"}
    assert [r.status for r in run if r.resource_id in ("rs-pump-3", "rs-pump-4")] == ["free", "free"]
