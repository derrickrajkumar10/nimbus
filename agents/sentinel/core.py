"""Sentinel (#9): score every Segment on each clock.tick, emit risk.changed only on band crossings.

The scoring itself belongs to the risk engine (#4). The Sentinel takes a `Scorer`:
any callable (segments, run_id, sim_time) -> list[SegmentRisk]. A Run starts from
Baseline Thresholds, so a Segment with no earlier risk in this Run counts as `low`.
"""

from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Protocol

from nimbus_contracts.common import RiskBand
from nimbus_contracts.entities import Segment, SegmentRisk
from nimbus_contracts.events import ClockTick, RiskChanged, RiskChangedDetail

from common.context import AgentContext
from sentinel.reasons import ReasonWriter

Scorer = Callable[[Sequence[Segment], str, datetime], list[SegmentRisk]]

START_BAND = RiskBand.LOW


class RiskStore(Protocol):
    def latest(self, run_id: str) -> dict[str, SegmentRisk]: ...
    def save(self, risks: Sequence[SegmentRisk]) -> None: ...


class MemoryRiskStore:
    """Latest SegmentRisk per Run and Segment, kept in memory.

    Stands in for the SegmentRisk table until #32 settles who writes it.
    """

    def __init__(self) -> None:
        self._by_run: dict[str, dict[str, SegmentRisk]] = {}

    def latest(self, run_id: str) -> dict[str, SegmentRisk]:
        return dict(self._by_run.get(run_id, {}))

    def save(self, risks: Sequence[SegmentRisk]) -> None:
        for risk in risks:
            self._by_run.setdefault(risk.run_id, {})[risk.segment_id] = risk


def run_tick(
    ctx: AgentContext,
    tick: ClockTick,
    *,
    segments: Sequence[Segment],
    scorer: Scorer,
    store: RiskStore,
    reasons: ReasonWriter,
) -> list[RiskChanged]:
    """Score every Segment for this tick, emit risk.changed for each band crossing, log one activity line."""
    previous = store.latest(tick.run_id)
    risks = scorer(segments, tick.run_id, tick.sim_time)
    names = {s.segment_id: s.street_name or s.segment_id for s in segments}

    changes: list[RiskChanged] = []
    for risk in risks:
        before = previous[risk.segment_id].band if risk.segment_id in previous else START_BAND
        if risk.band == before:
            continue
        plain = [reasons.plain(risk.reasons[0]), *risk.reasons[1:]] if risk.reasons else []
        changes.append(
            ctx.publish(
                RiskChanged,
                RiskChangedDetail(
                    segment_id=risk.segment_id,
                    previous_band=before,
                    band=risk.band,
                    score=risk.score,
                    minutes_to_flood=risk.minutes_to_flood,
                    reasons=plain,
                ),
            )
        )
    store.save(risks)

    source = getattr(scorer, "label", "risk engine")
    ctx.activity(
        saw=f"Tick {tick.tick_index} at {tick.sim_time:%d %b %Y %H:%M}: scored {len(risks)} Segments ({source})",
        decided=f"{len(changes)} band change{'' if len(changes) == 1 else 's'}" if changes else "No band changes",
        why=_summary(changes, names),
    )
    return changes


def _summary(changes: Sequence[RiskChanged], names: dict[str, str], limit: int = 3) -> str:
    if not changes:
        return "Every Segment stayed in its band"
    parts = [f"{names.get(c.detail.segment_id, c.detail.segment_id)} {c.detail.previous_band}→{c.detail.band}" for c in changes[:limit]]
    more = len(changes) - limit
    return "; ".join(parts) + (f"; and {more} more" if more > 0 else "")
