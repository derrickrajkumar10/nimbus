"""NimbusApi: the projector and the console API each get the right trigger, the right tables and nothing more."""

import json

import aws_cdk as cdk
import pytest
from aws_cdk import assertions

from stacks.api import (
    CONSOLE_READ_TABLES,
    CONSOLE_ROUTES,
    CONSOLE_UPDATED_TABLE,
    PROJECTED_EVENT_TYPES,
    WRITTEN_TABLES,
    NimbusApi,
)
from stacks.shared import TABLES, NimbusShared


@pytest.fixture(scope="module")
def template() -> assertions.Template:
    # Bundling needs Docker or Podman; the asset's contents aren't under test here.
    app = cdk.App(context={"aws:cdk:bundling-stacks": []})
    env = cdk.Environment(account="123456789012", region="us-east-1")
    shared = NimbusShared(app, "NimbusShared", env=env)
    return assertions.Template.from_stack(NimbusApi(app, "NimbusApi", shared=shared, env=env))


def statements_for(template, role_prefix):
    """IAM statements attached to the role whose logical id starts with `role_prefix`."""
    out = []
    for policy in template.find_resources("AWS::IAM::Policy").values():
        roles = [r.get("Ref", "") for r in policy["Properties"]["Roles"]]
        if any(r.startswith(role_prefix) for r in roles):
            out += policy["Properties"]["PolicyDocument"]["Statement"]
    return out


def actions(statement):
    return [statement["Action"]] if isinstance(statement["Action"], str) else statement["Action"]


def dynamo_statements(template, role_prefix):
    return [s for s in statements_for(template, role_prefix) if any(a.startswith("dynamodb:") for a in actions(s))]


# --- projector -------------------------------------------------------------


def test_projector_lambda(template):
    env = {f"NIMBUS_TABLE_{name.upper()}": assertions.Match.any_value() for name in WRITTEN_TABLES}
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {"Runtime": "python3.12", "Handler": "projector.handler.handler", "Environment": {"Variables": env}},
    )


def test_rule_sends_projected_events_from_the_shared_bus_with_a_dead_letter_queue(template):
    template.has_resource_properties(
        "AWS::Events::Rule",
        {
            "EventPattern": {"source": [{"prefix": "nimbus."}], "detail-type": list(PROJECTED_EVENT_TYPES)},
            "Targets": assertions.Match.array_with(
                [assertions.Match.object_like({"DeadLetterConfig": assertions.Match.any_value(), "RetryPolicy": {"MaximumRetryAttempts": 2}})]
            ),
        },
    )
    template.resource_count_is("AWS::SQS::Queue", 1)


def test_projector_can_write_only_its_own_tables(template):
    granted = json.dumps(dynamo_statements(template, "ProjectorServiceRole"))
    for name in WRITTEN_TABLES:
        assert f"{name}Table" in granted, name
    for table in TABLES:
        if table.name not in WRITTEN_TABLES:
            assert f"{table.name}Table" not in granted, f"projector must not touch {table.name}"
    assert "dynamodb:GetItem" not in granted  # write access only


def test_projected_tables_are_run_scoped_tables():
    assert {t.name for t in TABLES if t.name in WRITTEN_TABLES} == set(WRITTEN_TABLES)
    assert all(t.pk == "run_id" for t in TABLES if t.name in WRITTEN_TABLES)


# --- console API -----------------------------------------------------------


def test_console_api_exposes_exactly_the_routes(template):
    keys = {r["Properties"]["RouteKey"] for r in template.find_resources("AWS::ApiGatewayV2::Route").values()}
    assert keys == {f"{method} {path}" for method, path in CONSOLE_ROUTES}
    template.has_resource_properties("AWS::ApiGatewayV2::Api", {"ProtocolType": "HTTP", "Name": "nimbus-console"})


def test_console_lambda_reads_what_it_serves_and_updates_only_proposals(template):
    dynamo = dynamo_statements(template, "ConsoleServiceRole")
    reads = json.dumps([s for s in dynamo if "dynamodb:Query" in actions(s)])
    for name in CONSOLE_READ_TABLES:
        assert f"{name}Table" in reads, name
    others = {t.name for t in TABLES} - set(CONSOLE_READ_TABLES)
    assert others and all(f"{name}Table" not in json.dumps(dynamo) for name in others), "console touches only what it serves"

    forbidden = {"dynamodb:PutItem", "dynamodb:DeleteItem", "dynamodb:BatchWriteItem"}
    assert [s for s in dynamo if forbidden & set(actions(s))] == [], "the console never puts or deletes rows"
    updates = [s for s in dynamo if "dynamodb:UpdateItem" in actions(s)]
    assert len(updates) == 1 and actions(updates[0]) == ["dynamodb:UpdateItem"]
    assert f"{CONSOLE_UPDATED_TABLE}Table" in json.dumps(updates)


def test_console_lambda_publishes_events_and_knows_the_bus(template):
    assert any("events:PutEvents" in actions(s) for s in statements_for(template, "ConsoleServiceRole"))
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Handler": "console.handler.handler",
            "Environment": {"Variables": assertions.Match.object_like({"NIMBUS_EVENT_BUS": assertions.Match.any_value()})},
        },
    )


def test_console_api_is_throttled(template):
    stages = [r["Properties"] for r in template.find_resources("AWS::ApiGatewayV2::Stage").values()]
    assert stages and all(s["StageName"] == "$default" and s["AutoDeploy"] is True for s in stages)
    assert all(
        s["DefaultRouteSettings"] == {"ThrottlingBurstLimit": 50, "ThrottlingRateLimit": 25} for s in stages
    ), "an open API needs a rate ceiling until #19 adds auth"


def test_console_url_is_published(template):
    template.has_resource_properties("AWS::SSM::Parameter", {"Name": "/nimbus/api/console-url"})
