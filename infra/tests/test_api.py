"""NimbusApi's projector: right trigger, right tables, nothing more."""

import json

import aws_cdk as cdk
import pytest
from aws_cdk import assertions

from stacks.api import PROJECTED_EVENT_TYPES, WRITTEN_TABLES, NimbusApi
from stacks.shared import TABLES, NimbusShared


@pytest.fixture(scope="module")
def template() -> assertions.Template:
    # Bundling needs Docker or Podman; the asset's contents aren't under test here.
    app = cdk.App(context={"aws:cdk:bundling-stacks": []})
    env = cdk.Environment(account="123456789012", region="us-east-1")
    shared = NimbusShared(app, "NimbusShared", env=env)
    return assertions.Template.from_stack(NimbusApi(app, "NimbusApi", shared=shared, env=env))


def test_projector_lambda(template):
    env = {f"NIMBUS_TABLE_{name.upper()}": assertions.Match.any_value() for name in WRITTEN_TABLES}
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Runtime": "python3.12",
            "Handler": "projector.handler.handler",
            "Environment": {"Variables": env},
        },
    )


def test_rule_sends_projected_events_from_the_shared_bus_with_a_dead_letter_queue(template):
    template.has_resource_properties(
        "AWS::Events::Rule",
        {
            "EventPattern": {
                "source": [{"prefix": "nimbus."}],
                "detail-type": list(PROJECTED_EVENT_TYPES),
            },
            "Targets": assertions.Match.array_with(
                [assertions.Match.object_like({"DeadLetterConfig": assertions.Match.any_value(), "RetryPolicy": {"MaximumRetryAttempts": 2}})]
            ),
        },
    )
    template.resource_count_is("AWS::SQS::Queue", 1)


def test_projector_can_write_only_its_own_tables(template):
    statements = [
        s
        for policy in template.find_resources("AWS::IAM::Policy").values()
        for s in policy["Properties"]["PolicyDocument"]["Statement"]
        if any(a.startswith("dynamodb:") for a in ([s["Action"]] if isinstance(s["Action"], str) else s["Action"]))
    ]
    granted = json.dumps(statements)
    for name in WRITTEN_TABLES:
        assert f"{name}Table" in granted, name
    for table in TABLES:
        if table.name not in WRITTEN_TABLES:
            assert f"{table.name}Table" not in granted, f"projector must not touch {table.name}"
    assert "dynamodb:GetItem" not in granted  # write access only


def test_projected_tables_are_run_scoped_tables():
    assert {t.name for t in TABLES if t.name in WRITTEN_TABLES} == set(WRITTEN_TABLES)
    assert all(t.pk == "run_id" for t in TABLES if t.name in WRITTEN_TABLES)
