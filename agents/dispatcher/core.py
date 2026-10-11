"""Dispatcher (#18): Work Order Proposals from the dispatch solver, never a dispatch on its own.

After each Sentinel tick it asks the solver (engines/dispatch, #16) which free Resource
should go to which flooded or likely Segment, and proposes each pick as a Work Order for
an officer. The maths decides the ranking; the agent checks Cedar, writes the Proposal
and says why in the feed. Only an approved `proposal.decided` moves a crew (Cedar's
`crew-dispatch-needs-approval`), and then the Dispatcher marks the Resource `en_route`.

A Resource or Segment that already has a pending or approved Work Order in the Run is
left out, so each tick proposes only new work. A Segment whose Work Order an officer
rejected isn't proposed again in that Run; the Resource is free for the next one.
"""

from collections.abc import Callable, Sequence
from typing import Protocol

from dispatch.solver import TRAVEL_OFFSET_MINUTES
from nimbus_contracts.common import RiskBand
from nimbus_contracts.entities import Proposal, ProposalStatus, Resource, ResourceStatus, Segment, WorkOrder
from nimbus_contracts.events import AgentActivity, ProposalCreated, ProposalDecided

from common.context import AgentContext
from common.ids import new_id
from sentinel.core import RiskStore

NEEDS = (RiskBand.FLOODED, RiskBand.LIKELY)
APPROVED = (ProposalStatus.APPROVED, ProposalStatus.EDITED)


class Resources(Protocol):
    def for_run(self, run_id: str) -> list[Resource]: ...
    def set_status(self, run_id: str, resource_id: str, status: ResourceStatus) -> bool: ...


class Proposals(Protocol):
    def by_agent(self, run_id: str, agent: str) -> list[Proposal]: ...


Solver = Callable[..., list]


class Dispatcher:
    def __init__(self, *, segments: Sequence[Segment], risks: RiskStore, resources: Resources, proposals: Proposals, solver: Solver) -> None:
        self.segments = {s.segment_id: s for s in segments}
        self.risks = risks
        self.resources = resources
        self.proposals = proposals
        self.solver = solver
        # Proposed while warm, for the second or so before the projector writes them to Proposals.
        self._recent: dict[str, set[tuple[str, str]]] = {}

    def street(self, segment_id: str) -> str:
        segment = self.segments.get(segment_id)
        return (segment.street_name if segment else None) or segment_id

    # --- after each Sentinel tick -------------------------------------------

    def on_sentinel_tick(self, ctx: AgentContext, event: AgentActivity) -> None:
        run_id = event.run_id
        current = self.risks.latest(run_id)
        if not any(r.band in NEEDS for r in current.values()):
            return  # nothing to send anyone to: stay out of the feed

        mine = self.proposals.by_agent(run_id, ctx.agent.value)
        decided = {(p.action.resource_id, p.action.segment_id) for p in mine}
        open_work = {(p.action.resource_id, p.action.segment_id) for p in mine if p.status != ProposalStatus.REJECTED}
        open_work |= self._recent.get(run_id, set()) - decided
        busy_resources = {resource_id for resource_id, _ in open_work}
        closed_segments = {p.action.segment_id for p in mine} | {segment_id for _, segment_id in open_work}

        resources = [r for r in self.resources.for_run(run_id) if r.resource_id not in busy_resources]
        segments = [s for s in self.segments.values() if s.segment_id not in closed_segments]
        picks = self.solver(segments, list(current.values()), resources, run_id=run_id, sim_time=ctx.sim_time)
        if not picks:
            return  # every free Resource is already proposed or out: nothing new to say

        proposed = []
        for rank, pick in enumerate(picks, start=1):
            proposal_id = new_id("pr", ctx.sim_time, seed=f"{run_id}|dispatcher|{pick.resource_id}|{pick.segment_id}")
            decision = ctx.cedar_check(
                "ProposeWorkOrder",
                f'WorkOrder::"{proposal_id}"',
                resource_attrs={"resource_id": pick.resource_id, "segment_id": pick.segment_id},
            )
            if not decision.allowed:
                ctx.activity(saw=pick.reason, decided="Work Order blocked", why=decision.reason)
                continue
            ctx.publish(
                ProposalCreated,
                Proposal(
                    proposal_id=proposal_id,
                    run_id=run_id,
                    proposed_by=ctx.agent,
                    created_at=ctx.sim_time,
                    rank=rank,
                    reason=f"{pick.reason} Score {pick.score:.1f} = impact {pick.numbers['impact']:g} ÷ ({pick.travel_minutes:g} min travel + {TRAVEL_OFFSET_MINUTES:g} min to set off).",
                    action=WorkOrder(
                        resource_id=pick.resource_id,
                        segment_id=pick.segment_id,
                        buildings_affected=pick.buildings_affected,
                        reading_ids=list(pick.reading_ids),
                        sos_ids=list(pick.sos_ids),
                    ),
                ),
            )
            proposed.append(pick)
            self._recent.setdefault(run_id, set()).add((pick.resource_id, pick.segment_id))

        if proposed:
            needs = sum(1 for r in current.values() if r.band in NEEDS)
            ctx.activity(
                saw=f"{needs} Segment{'' if needs == 1 else 's'} likely or flooded; {len(resources)} Resource{'' if len(resources) == 1 else 's'} not yet assigned",
                decided=f"Proposed {len(proposed)} Work Order{'' if len(proposed) == 1 else 's'} for officer approval",
                why=" ".join(p.reason for p in proposed),
            )

    # --- an officer decided -------------------------------------------------

    def on_proposal_decided(self, ctx: AgentContext, event: ProposalDecided) -> None:
        d = event.detail
        order = d.proposal.action
        if order.kind != "work_order":
            return
        street = self.street(order.segment_id)
        saw = f"Officer {d.decided_by} {d.decision} Work Order {d.proposal_id}"
        if d.decision not in APPROVED:
            ctx.activity(saw=saw, decided="No crew moved", why=f"{order.resource_id} stays available; it won't be proposed for {street} again")
            return
        decision = ctx.cedar_check(
            "DispatchCrew",
            f'WorkOrder::"{d.proposal_id}"',
            resource_attrs={"resource_id": order.resource_id, "segment_id": order.segment_id},
            context={"officer_approved": True},
        )
        if not decision.allowed:
            ctx.activity(saw=saw, decided="Dispatch blocked", why=decision.reason)
            return
        if not self.resources.set_status(event.run_id, order.resource_id, ResourceStatus.EN_ROUTE):
            ctx.activity(saw=saw, decided="Dispatch failed", why=f"{order.resource_id} isn't a Resource in this Run")
            return
        label = next((r.label for r in self.resources.for_run(event.run_id) if r.resource_id == order.resource_id), order.resource_id)
        ctx.activity(saw=saw, decided=f"{label} en route to {street}", why=f"Approved by {d.decided_by}; {order.buildings_affected} buildings nearby")
