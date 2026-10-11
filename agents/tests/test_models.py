"""Model settings and the Strands factory. Bedrock calls go to botocore's Stubber,
a fake AWS on this machine, with fake keys: no request leaves, no credits are used."""

import boto3
import pytest
from botocore.stub import ANY, Stubber
from nimbus_contracts.common import Agent

from common.models import AGENT_MODELS, DEFAULT_MODEL_IDS, MODEL_ID_ENV, Tier, build_agent, model_id


def fake_session() -> boto3.Session:
    return boto3.Session(aws_access_key_id="fake", aws_secret_access_key="fake", region_name="us-east-1")


def fake_reply(text: str) -> dict:
    return {
        "output": {"message": {"role": "assistant", "content": [{"text": text}]}},
        "stopReason": "end_turn",
        "usage": {"inputTokens": 40, "outputTokens": 12, "totalTokens": 52},
        "metrics": {"latencyMs": 5},
    }


@pytest.fixture(autouse=True)
def no_model_overrides(monkeypatch):
    for env in MODEL_ID_ENV.values():
        monkeypatch.delenv(env, raising=False)


def test_every_agent_has_model_settings():
    assert set(AGENT_MODELS) == set(Agent)


def test_pro_only_for_dispatcher_commander_chronicler():
    # ADR 0004: Lite for high-volume and vision steps, Pro for planning and writing.
    pro = {agent for agent, settings in AGENT_MODELS.items() if settings.tier is Tier.PRO}
    assert pro == {Agent.DISPATCHER, Agent.COMMANDER, Agent.CHRONICLER}


def test_model_ids_default_and_override(monkeypatch):
    assert model_id(Agent.HERALD) == DEFAULT_MODEL_IDS[Tier.LITE]
    assert model_id(Agent.COMMANDER) == DEFAULT_MODEL_IDS[Tier.PRO]
    monkeypatch.setenv(MODEL_ID_ENV[Tier.LITE], "amazon.nova-lite-v1:0")
    assert model_id(Agent.HERALD) == "amazon.nova-lite-v1:0"
    assert model_id(Agent.COMMANDER) == DEFAULT_MODEL_IDS[Tier.PRO]


@pytest.mark.parametrize("agent", [Agent.SENTINEL, Agent.DISPATCHER])
def test_agent_sends_its_model_and_cost_cap_to_bedrock(agent):
    settings = AGENT_MODELS[agent]
    strands_agent = build_agent(agent, "You rewrite flood risk reasons as one plain sentence.", boto_session=fake_session())
    client = strands_agent.model.client
    expected_request = {
        "modelId": model_id(agent),
        "inferenceConfig": {"maxTokens": settings.max_tokens, "temperature": settings.temperature},
        "messages": ANY,
        "system": ANY,
    }

    with Stubber(client) as stub:
        stub.add_response("converse", fake_reply("Likely waterlogged within 2 hours."), expected_request)
        answer = strands_agent("Reason: 3 verified knee-deep Readings upstream")
        stub.assert_no_pending_responses()

    assert str(answer).strip() == "Likely waterlogged within 2 hours."


def test_system_prompt_reaches_bedrock():
    strands_agent = build_agent(Agent.HERALD, "Write alerts in English and Tamil.", boto_session=fake_session())
    client = strands_agent.model.client
    seen = {}
    client.meta.events.register("provide-client-params.bedrock-runtime.Converse", lambda params, **_: seen.update(params))

    with Stubber(client) as stub:
        stub.add_response("converse", fake_reply("ok"))
        strands_agent("hello")

    assert seen["system"] == [{"text": "Write alerts in English and Tamil."}]
