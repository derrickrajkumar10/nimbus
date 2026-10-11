"""Dispatcher Lambda: wakes after each Sentinel tick (its agent.activity line) and on proposal.decided.

The Sentinel writes SegmentRisk before its tick's activity line, so waking on that line
gives one run per tick on a settled picture. Resources, Proposals and SegmentRisk come
from DynamoDB when their table env vars are set (always, when deployed); otherwise the
fixture Resources and in-memory stand-ins, for local runs.
"""

import json
from functools import cache
from pathlib import Path

from nimbus_contracts.common import Agent
from nimbus_contracts.entities import Resource

from common.context import AgentContext
from common.runtime import make_handler
from dispatcher.core import Dispatcher
from dispatcher.store import DynamoProposals, DynamoResources, MemoryProposals, MemoryResources
from sentinel.core import MemoryRiskStore
from sentinel.fixtures import FIXTURES, load_segments
from sentinel.store import DynamoRiskStore


def _fixture_resources() -> MemoryResources:
    rows = json.loads(Path(FIXTURES, "resources.json").read_text())
    return MemoryResources(template=[Resource.model_validate(row) for row in rows])


@cache
def _dispatcher() -> Dispatcher:
    from dispatch import rank_work_orders  # engines/dispatch, bundled beside the agents

    return Dispatcher(
        segments=load_segments(),
        risks=DynamoRiskStore.from_env() or MemoryRiskStore(),
        resources=DynamoResources.from_env() or _fixture_resources(),
        proposals=DynamoProposals.from_env() or MemoryProposals(),
        solver=rank_work_orders,
    )


def handle(ctx: AgentContext, event) -> None:
    if event.type == "agent.activity" and event.detail.agent == Agent.SENTINEL:
        _dispatcher().on_sentinel_tick(ctx, event)
    elif event.type == "proposal.decided":
        _dispatcher().on_proposal_decided(ctx, event)


handler = make_handler(Agent.DISPATCHER, handle)
