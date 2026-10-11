"""NimbusShared must match contracts/storage.md, because every lane builds against it."""

import re
from pathlib import Path

import aws_cdk as cdk
import pytest
from aws_cdk import assertions

from stacks.shared import TABLES, NimbusShared, table_name

STORAGE_MD = Path(__file__).resolve().parents[2] / "contracts" / "storage.md"


def storage_md_tables() -> dict[str, tuple[str, str | None]]:
    """Table name -> (partition key, sort key) from the markdown table in storage.md."""
    tables = {}
    for line in STORAGE_MD.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or not re.fullmatch(r"`\w+`", cells[0]):
            continue
        pk = cells[1].strip("`")
        sk = cells[2].strip("`") or None
        tables[cells[0].strip("`")] = (pk, sk)
    return tables


@pytest.fixture(scope="module")
def template() -> assertions.Template:
    app = cdk.App()
    stack = NimbusShared(app, "NimbusShared", env=cdk.Environment(account="123456789012", region="us-east-1"))
    return assertions.Template.from_stack(stack)


def test_storage_md_was_parsed():
    assert len(storage_md_tables()) == 16


def test_tables_match_storage_md():
    assert {t.name: (t.pk, t.sk) for t in TABLES} == storage_md_tables()


def test_every_table_is_on_demand_and_keyed_as_documented(template):
    for name, (pk, sk) in storage_md_tables().items():
        schema = [{"AttributeName": pk, "KeyType": "HASH"}]
        if sk:
            schema.append({"AttributeName": sk, "KeyType": "RANGE"})
        template.has_resource_properties(
            "AWS::DynamoDB::Table",
            {"TableName": table_name(name), "KeySchema": schema, "BillingMode": "PAY_PER_REQUEST"},
        )
    template.resource_count_is("AWS::DynamoDB::Table", 16)


def test_mutable_tables_lead_with_run_id():
    # ADR 0001: a query that forgets the Run must not be possible on a mutable table.
    run_scoped = {t.name for t in TABLES if t.pk.startswith("run_id")}
    static = {t.name for t in TABLES} - run_scoped
    assert static == {"Segments", "Devices", "SavedPlaces"}


def test_event_bus_and_archive(template):
    template.has_resource_properties("AWS::Events::EventBus", {"Name": "nimbus"})
    template.has_resource_properties(
        "AWS::Events::Archive",
        {"EventPattern": {"source": [{"prefix": "nimbus."}]}, "RetentionDays": 7},
    )


def test_two_private_buckets(template):
    template.resource_count_is("AWS::S3::Bucket", 2)
    template.has_resource_properties(
        "AWS::S3::Bucket",
        {"PublicAccessBlockConfiguration": {"BlockPublicAcls": True, "BlockPublicPolicy": True}},
    )


def test_names_are_published_to_ssm(template):
    names = {
        "/nimbus/bus/name",
        "/nimbus/bus/arn",
        "/nimbus/buckets/photos",
        "/nimbus/buckets/data",
        *(f"/nimbus/tables/{t.name}" for t in TABLES),
    }
    published = {
        r["Properties"]["Name"] for r in template.find_resources("AWS::SSM::Parameter").values()
    }
    assert names == published


def test_segments_survive_stack_deletion(template):
    template.has_resource(
        "AWS::DynamoDB::Table",
        {"Properties": {"TableName": "nimbus-Segments"}, "DeletionPolicy": "Retain"},
    )
