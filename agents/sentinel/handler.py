"""Sentinel Lambda: wakes on clock.tick.

Runs on practice data until the risk engine (#4) and the SegmentRisk table (#32)
are connected; swap the scorer and store in `_defaults` when they are.
"""

from functools import cache

from nimbus_contracts.common import Agent

from common.context import AgentContext
from common.runtime import make_handler
from sentinel.core import MemoryRiskStore, run_tick
from sentinel.fixtures import FixtureScorer, load_segments
from sentinel.reasons import ReasonWriter


@cache
def _defaults() -> dict:
    # Built on first tick, then reused while the Lambda stays warm.
    return {
        "segments": load_segments(),
        "scorer": FixtureScorer(),
        "store": MemoryRiskStore(),
        "reasons": ReasonWriter(),
    }


def handle(ctx: AgentContext, event) -> None:
    if event.type != "clock.tick":
        return
    run_tick(ctx, event, **_defaults())


handler = make_handler(Agent.SENTINEL, handle)
