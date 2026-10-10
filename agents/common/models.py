"""Which Amazon Nova model each agent uses (ADR 0004), and a Strands agent factory.

Model IDs live only here. The defaults are the us-east-1 inference profiles for
Nova Lite and Pro; confirm them against the IDs posted on issue #1, and override
per deploy with NIMBUS_NOVA_LITE_ID / NIMBUS_NOVA_PRO_ID without a code change.

max_tokens caps every answer's length, and so the cost of every Bedrock call.
"""

import os
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from nimbus_contracts.common import Agent
from strands import Agent as StrandsAgent
from strands.models.bedrock import BedrockModel

REGION = "us-east-1"  # ADR 0004


class Tier(StrEnum):
    LITE = "lite"  # high-volume and vision steps
    PRO = "pro"  # Dispatcher, Commander, Chronicler


DEFAULT_MODEL_IDS = {
    Tier.LITE: "us.amazon.nova-lite-v1:0",
    Tier.PRO: "us.amazon.nova-pro-v1:0",
}
MODEL_ID_ENV = {Tier.LITE: "NIMBUS_NOVA_LITE_ID", Tier.PRO: "NIMBUS_NOVA_PRO_ID"}


@dataclass(frozen=True)
class ModelSettings:
    tier: Tier
    max_tokens: int
    temperature: float


AGENT_MODELS: dict[Agent, ModelSettings] = {
    Agent.SENTINEL: ModelSettings(Tier.LITE, max_tokens=200, temperature=0.2),
    Agent.VERIFIER: ModelSettings(Tier.LITE, max_tokens=512, temperature=0.0),
    Agent.TRIAGE: ModelSettings(Tier.LITE, max_tokens=512, temperature=0.2),
    Agent.PATHFINDER: ModelSettings(Tier.LITE, max_tokens=512, temperature=0.2),
    Agent.HERALD: ModelSettings(Tier.LITE, max_tokens=400, temperature=0.3),
    Agent.DISPATCHER: ModelSettings(Tier.PRO, max_tokens=1024, temperature=0.2),
    Agent.CHRONICLER: ModelSettings(Tier.PRO, max_tokens=2048, temperature=0.3),
    Agent.COMMANDER: ModelSettings(Tier.PRO, max_tokens=2048, temperature=0.2),
}


def model_id(agent: Agent) -> str:
    tier = AGENT_MODELS[agent].tier
    return os.environ.get(MODEL_ID_ENV[tier]) or DEFAULT_MODEL_IDS[tier]


def bedrock_model(agent: Agent, *, boto_session: Any = None) -> BedrockModel:
    """The agent's Nova model on Bedrock. Nothing is called until the agent is asked something."""
    settings = AGENT_MODELS[agent]
    region = None if boto_session is not None else REGION  # a session carries its own region
    return BedrockModel(
        boto_session=boto_session,
        region_name=region,
        model_id=model_id(agent),
        max_tokens=settings.max_tokens,
        temperature=settings.temperature,
        streaming=False,  # Lambdas don't stream; one Converse call per model turn
    )


def build_agent(
    agent: Agent,
    system_prompt: str,
    tools: Sequence[Any] = (),
    *,
    model: Any = None,
    boto_session: Any = None,
) -> StrandsAgent:
    """A Strands agent for `agent`, on its configured Nova model unless `model` is given."""
    return StrandsAgent(
        model=model or bedrock_model(agent, boto_session=boto_session),
        system_prompt=system_prompt,
        tools=list(tools),
        name=agent.value,
        callback_handler=None,  # don't print model output to Lambda logs
    )
