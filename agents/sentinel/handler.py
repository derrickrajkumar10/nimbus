"""Sentinel Lambda: wakes on clock.tick.

A Michaung Replay (`replay-michaung…`) is scored by the risk engine's MichaungScorer
(engines/risk, #4) on archived Open-Meteo rain; any other Run falls back to the
practice fixtures until a live RainSource is wired. The activity line names which.
Previous bands live in the SegmentRisk table when NIMBUS_TABLE_SEGMENTRISK is set
(always, when deployed), so a cold start or a second copy doesn't re-flag every
Segment (#42).
"""

from functools import cache

from nimbus_contracts.common import Agent

from common.context import AgentContext
from common.runtime import make_handler
from sentinel.core import MemoryRiskStore, run_tick
from sentinel.fixtures import FixtureScorer, load_segments
from sentinel.reasons import ReasonWriter
from sentinel.store import DynamoRiskStore

MICHAUNG_RUN_PREFIX = "replay-michaung"


@cache
def _defaults() -> dict:
    # Built on first tick, then reused while the Lambda stays warm.
    return {
        "segments": load_segments(),
        "store": DynamoRiskStore.from_env() or MemoryRiskStore(),
        "reasons": ReasonWriter(),
    }


@cache
def _michaung_scorer():
    """The risk engine's scorer, or None where engines/risk isn't importable (it is in the bundle)."""
    try:
        from risk import MichaungScorer
    except ImportError:
        return None
    return MichaungScorer()


def scorer_for(run_id: str):
    if run_id.startswith(MICHAUNG_RUN_PREFIX):
        michaung = _michaung_scorer()
        if michaung is not None:
            return michaung
    return FixtureScorer()


def handle(ctx: AgentContext, event) -> None:
    if event.type != "clock.tick":
        return
    try:
        run_tick(ctx, event, scorer=scorer_for(event.run_id), **_defaults())
    except ValueError as exc:
        # The risk engine refuses times outside its rain data (it needs 72 h before, 3 h after).
        # Skip the tick instead of failing, so EventBridge doesn't retry it.
        if "rain covers" not in str(exc):
            raise
        ctx.activity(saw=f"Tick {event.tick_index} at {event.sim_time:%d %b %Y %H:%M}", decided="Skipped this tick", why=str(exc))


handler = make_handler(Agent.SENTINEL, handle)
