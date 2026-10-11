"""Sentinel Lambda: wakes on clock.tick.

Scores practice data until the risk engine (#4) lands. Previous bands live in the
SegmentRisk table when NIMBUS_TABLE_SEGMENTRISK is set (always, when deployed),
so a cold start or a second copy doesn't re-flag every Segment (#42).
"""

from functools import cache

from nimbus_contracts.common import Agent

from common.context import AgentContext
from common.runtime import make_handler
from sentinel.core import MemoryRiskStore, run_tick
from sentinel.fixtures import FixtureScorer, load_segments
from sentinel.reasons import ReasonWriter
from sentinel.store import DynamoRiskStore


@cache
def _defaults() -> dict:
    # Built on first tick, then reused while the Lambda stays warm.
    return {
        "segments": load_segments(),
        "scorer": FixtureScorer(),
        "store": DynamoRiskStore.from_env() or MemoryRiskStore(),
        "reasons": ReasonWriter(),
    }


def handle(ctx: AgentContext, event) -> None:
    if event.type != "clock.tick":
        return
    run_tick(ctx, event, **_defaults())


handler = make_handler(Agent.SENTINEL, handle)
