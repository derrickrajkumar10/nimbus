"""NimbusAgents: rules wake agents on real contract events, and agents can't write the projector's tables.

Bundling is skipped (aws:cdk:bundling-stacks = []), so no container runtime is needed.
"""

from pathlib import Path

import aws_cdk as cdk
import pytest
from aws_cdk import assertions

from stacks.agents import AGENTS, PROJECTOR_TABLES, NimbusAgents

EVENTS_DIR = Path(__file__).resolve().parents[2] / "contracts" / "schema" / "events"
CONTRACT_EVENT_TYPES = {p.name.removesuffix(".schema.json") for p in EVENTS_DIR.glob("*.schema.json")} - {"Event"}


def synth(**context) -> dict:
    app = cdk.App(context={"aws:cdk:bundling-stacks": [], **context})
    stack = NimbusAgents(app, "NimbusAgents", env=cdk.Environment(account="123456789012", region="us-east-1"))
    return assertions.Template.from_stack(stack).to_json()


@pytest.fixture(scope="module")
def template() -> dict:
    return synth()


def resources(template, kind):
    return {k: v for k, v in template["Resources"].items() if v["Type"] == kind}


def ssm_parameter_names(template) -> dict[str, str]:
    """CloudFormation parameter logical ID -> SSM path it resolves."""
    return {k: v["Default"] for k, v in template.get("Parameters", {}).items() if "SSM" in v["Type"]}


def refs(value) -> set[str]:
    found = set()
    if isinstance(value, dict):
        if "Ref" in value and not value["Ref"].startswith("AWS::"):  # skip AWS::Partition, AWS::AccountId, ...
            found.add(value["Ref"])
        for v in value.values():
            found |= refs(v)
    elif isinstance(value, list):
        for v in value:
            found |= refs(v)
    return found


def statements(template):
    for policy in resources(template, "AWS::IAM::Policy").values():
        for st in policy["Properties"]["PolicyDocument"]["Statement"]:
            actions = st["Action"] if isinstance(st["Action"], list) else [st["Action"]]
            yield policy, actions, st["Resource"]


def test_contract_event_types_were_found():
    assert {"clock.tick", "risk.changed", "proposal.decided"} <= CONTRACT_EVENT_TYPES


def test_every_rule_wakes_on_a_real_contract_event(template):
    rules = resources(template, "AWS::Events::Rule")
    assert len(rules) == sum(len(a.wakes_on) for a in AGENTS)
    for rule in rules.values():
        [detail_type] = rule["Properties"]["EventPattern"]["detail-type"]
        assert detail_type in CONTRACT_EVENT_TYPES


def test_rules_are_on_the_shared_bus_from_ssm(template):
    params = ssm_parameter_names(template)
    for rule in resources(template, "AWS::Events::Rule").values():
        assert {params.get(r) for r in refs(rule["Properties"]["EventBusName"])} == {"/nimbus/bus/name"}


def test_no_agent_can_write_the_projectors_tables(template):
    params = ssm_parameter_names(template)
    forbidden = {f"/nimbus/tables/{t}" for t in PROJECTOR_TABLES}
    for _, actions, resource in statements(template):
        writes = [a for a in actions if a.startswith("dynamodb:") and a.split(":")[1] in {"PutItem", "UpdateItem", "DeleteItem", "BatchWriteItem"}]
        if writes:
            touched = {params.get(r) for r in refs(resource)}
            assert not touched & forbidden, f"{writes} on {touched & forbidden}"


def test_each_agent_writes_only_the_table_it_owns(template):
    params = ssm_parameter_names(template)
    written = set()
    for _, actions, resource in statements(template):
        if any(a == "dynamodb:PutItem" for a in actions):
            written |= {params.get(r) for r in refs(resource)}
    assert written == {"/nimbus/tables/SegmentRisk"}  # Sentinel (#9); later agents add theirs


def test_lambdas_run_python_312_with_the_bus_name_from_ssm(template):
    params = ssm_parameter_names(template)
    functions = resources(template, "AWS::Lambda::Function")
    assert len(functions) == len(AGENTS)
    for fn in functions.values():
        props = fn["Properties"]
        assert props["Runtime"] == "python3.12"
        assert {params.get(r) for r in refs(props["Environment"]["Variables"]["NIMBUS_EVENT_BUS"])} == {"/nimbus/bus/name"}


def test_bedrock_covers_the_profile_and_every_routed_region(template):
    bedrock = [r for _, actions, r in statements(template) if "bedrock:InvokeModel" in actions]
    assert len(bedrock) == 1  # only the Sentinel calls Nova; the Herald uses templates
    text = str(bedrock[0])
    for region in ("us-east-1", "us-east-2", "us-west-2"):
        assert f"arn:aws:bedrock:{region}::foundation-model/amazon.nova-lite-v1:0" in text
    assert "inference-profile/us.amazon.nova-lite-v1:0" in text


def test_herald_can_invoke_send_push_by_its_agreed_name():
    disabled = synth(send_push_function="")
    assert not any("lambda:InvokeFunction" in actions for _, actions, _ in statements(disabled))
    with_sender = synth()  # default: nimbus-send-push, as NimbusApi names it
    invoke = [r for _, actions, r in statements(with_sender) if "lambda:InvokeFunction" in actions]
    assert len(invoke) == 1 and "function:nimbus-send-push" in str(invoke[0])
    herald_env = next(
        f["Properties"]["Environment"]["Variables"]
        for f in resources(with_sender, "AWS::Lambda::Function").values()
        if f["Properties"]["FunctionName"] == "nimbus-agent-herald"
    )
    assert herald_env["NIMBUS_SEND_PUSH_FUNCTION"] == "nimbus-send-push"


def test_each_agent_gets_the_table_names_it_reads_or_writes(template):
    """#42: without these env vars the agents would fall back to in-memory state."""
    params = ssm_parameter_names(template)
    env_by_fn = {
        f["Properties"]["FunctionName"]: f["Properties"]["Environment"]["Variables"]
        for f in resources(template, "AWS::Lambda::Function").values()
    }
    for spec in AGENTS:
        env = env_by_fn[f"nimbus-agent-{spec.name}"]
        tables = {k.removeprefix("NIMBUS_TABLE_"): {params.get(r) for r in refs(v)} for k, v in env.items() if k.startswith("NIMBUS_TABLE_")}
        assert tables == {t.upper(): {f"/nimbus/tables/{t}"} for t in (*spec.reads, *spec.writes)}


def test_logs_expire_after_a_week(template):
    for group in resources(template, "AWS::Logs::LogGroup").values():
        assert group["Properties"]["RetentionInDays"] == 7


def test_model_ids_come_from_context():
    t = synth(nova_lite_id="amazon.nova-lite-v1:0")
    env = next(iter(resources(t, "AWS::Lambda::Function").values()))["Properties"]["Environment"]["Variables"]
    assert env["NIMBUS_NOVA_LITE_ID"] == "amazon.nova-lite-v1:0"
