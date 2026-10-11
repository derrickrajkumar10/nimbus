"""NimbusApi: the projector and the console API each get the right trigger, the right tables and nothing more."""

import json

import aws_cdk as cdk
import pytest
from aws_cdk import assertions

from stacks.api import (
    CITIZEN_READ_TABLES,
    CITIZEN_ROUTES,
    CITIZEN_WRITE_TABLES,
    CONSOLE_READ_TABLES,
    CONSOLE_ROUTES,
    CONSOLE_UPDATED_TABLE,
    FIREBASE_SECRET,
    PUSH_FUNCTION_NAME,
    PUSH_TABLE,
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
    keys = {
        r["Properties"]["RouteKey"]
        for r in template.find_resources("AWS::ApiGatewayV2::Route").values()
        if "Console" in json.dumps(r["Properties"]["Target"])
    }
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


# --- citizen API -----------------------------------------------------------


def test_citizen_api_exposes_exactly_the_routes(template):
    names = {
        r["Properties"]["RouteKey"]
        for r in template.find_resources("AWS::ApiGatewayV2::Route").values()
        if "Citizen" in json.dumps(r["Properties"]["Target"])
    }
    assert names == {f"{method} {path}" for method, path in CITIZEN_ROUTES}
    template.has_resource_properties("AWS::ApiGatewayV2::Api", {"ProtocolType": "HTTP", "Name": "nimbus-citizen"})


def test_citizen_lambda_touches_only_its_tables(template):
    dynamo = dynamo_statements(template, "CitizenServiceRole")
    granted = json.dumps(dynamo)
    mine = {*CITIZEN_READ_TABLES, *CITIZEN_WRITE_TABLES}
    for name in mine:
        assert f"{name}Table" in granted, name
    for table in TABLES:
        if table.name not in mine:
            assert f"{table.name}Table" not in granted, f"citizen API must not touch {table.name}"


def test_citizen_lambda_cannot_write_what_it_only_reads_or_read_devices(template):
    dynamo = dynamo_statements(template, "CitizenServiceRole")
    for statement in dynamo:
        writes = {"dynamodb:PutItem", "dynamodb:DeleteItem", "dynamodb:UpdateItem", "dynamodb:BatchWriteItem"} & set(actions(statement))
        reads = {"dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"} & set(actions(statement))
        resource = json.dumps(statement["Resource"])
        if writes:
            assert not any(f"{name}Table" in resource for name in CITIZEN_READ_TABLES), "Segments, risk and Readings are read-only"
        if reads:
            assert "DevicesTable" not in resource, "device tokens are never read back through the API"


def test_both_apis_are_throttled_until_auth_exists(template):
    stages = [r["Properties"] for r in template.find_resources("AWS::ApiGatewayV2::Stage").values()]
    assert len(stages) == 2  # console and citizen
    assert all(s["DefaultRouteSettings"] == {"ThrottlingBurstLimit": 50, "ThrottlingRateLimit": 25} for s in stages)


def test_citizen_lambda_signs_uploads_only_under_reports(template):
    s3 = [s for s in statements_for(template, "CitizenServiceRole") if any(a.startswith("s3:") for a in actions(s))]
    assert s3, "the citizen API signs photo uploads"
    for statement in s3:
        assert "reports/*" in json.dumps(statement["Resource"]), "photo access is limited to the reports/ prefix"
    allowed = {a for s in s3 for a in actions(s)}
    assert "s3:PutObject" in allowed and "s3:GetObject*" in allowed
    assert not any(a in allowed for a in ("s3:DeleteObject", "s3:DeleteObject*", "s3:*"))


def test_citizen_lambda_publishes_events_and_may_invoke_only_the_pathfinder(template):
    statements = statements_for(template, "CitizenServiceRole")
    assert any("events:PutEvents" in actions(s) for s in statements)
    invokes = [s for s in statements if "lambda:InvokeFunction" in actions(s)]
    assert len(invokes) == 1 and "nimbus-pathfinder" in json.dumps(invokes[0]["Resource"])
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Handler": "citizen.handler.handler",
            "Environment": {
                "Variables": assertions.Match.object_like(
                    {
                        "NIMBUS_EVENT_BUS": assertions.Match.any_value(),
                        "NIMBUS_BUCKET_PHOTOS": assertions.Match.any_value(),
                        "NIMBUS_PATHFINDER_FUNCTION": "nimbus-pathfinder",
                        "NIMBUS_TABLE_REPORTS": assertions.Match.any_value(),
                    }
                )
            },
        },
    )


def test_reports_are_put_and_read_but_never_deleted(template):
    reports = [s for s in dynamo_statements(template, "CitizenServiceRole") if "ReportsTable" in json.dumps(s["Resource"])]
    assert sorted(a for s in reports for a in actions(s)) == ["dynamodb:GetItem", "dynamodb:PutItem"]


def test_citizen_url_is_published(template):
    template.has_resource_properties("AWS::SSM::Parameter", {"Name": "/nimbus/api/citizen-url"})


# --- push sender -----------------------------------------------------------


def test_the_push_lambda_has_the_name_the_agents_expect(template):
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {"FunctionName": PUSH_FUNCTION_NAME, "Handler": "push.handler.handler", "Runtime": "python3.12"},
    )
    template.has_resource_properties("AWS::SSM::Parameter", {"Name": "/nimbus/lambdas/send-push"})
    assert PUSH_FUNCTION_NAME == "nimbus-send-push"


def test_the_push_lambda_only_reads_and_deletes_devices(template):
    dynamo = dynamo_statements(template, "PushServiceRole")
    assert len(dynamo) == 1
    assert sorted(actions(dynamo[0])) == ["dynamodb:BatchGetItem", "dynamodb:DeleteItem"]
    assert f"{PUSH_TABLE}Table" in json.dumps(dynamo[0]["Resource"])
    for table in TABLES:
        if table.name != PUSH_TABLE:
            assert f"{table.name}Table" not in json.dumps(dynamo), table.name


def test_the_push_lambda_reads_the_firebase_secret_and_nothing_else_secret(template):
    secret_statements = [s for s in statements_for(template, "PushServiceRole") if any(a.startswith("secretsmanager:") for a in actions(s))]
    assert len(secret_statements) == 1
    assert set(actions(secret_statements[0])) == {"secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"}
    assert FIREBASE_SECRET.split("/")[1] in json.dumps(secret_statements[0]["Resource"])
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {"Handler": "push.handler.handler", "Environment": {"Variables": {"NIMBUS_TABLE_DEVICES": assertions.Match.any_value(), "NIMBUS_FIREBASE_SECRET": FIREBASE_SECRET}}},
    )
