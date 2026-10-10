"""Events on the EventBridge bus.

EventBridge mapping: `detail-type` = Event.type, `source` = "nimbus.<source>", `detail` = the whole Event.
"""

from typing import Annotated, Literal

from pydantic import AwareDatetime, Field

from .common import Agent, Contract, Reason, RiskBand, RunId, Score, SegmentId, SimTime
from .entities import Alert, Hazard, Proposal, ProposalStatus, RankedSos, Reading, Report, Sos


class _Event(Contract):
    event_id: str
    run_id: RunId
    sim_time: SimTime
    emitted_at: Annotated[AwareDatetime, Field(description="Wall time, for logs only. Domain logic uses sim_time.")]
    source: Annotated[str, Field(examples=["sentinel", "replay-driver", "console"])]


class ClockTick(_Event):
    type: Literal["clock.tick"] = "clock.tick"
    step_minutes: Annotated[int, Field(gt=0)] = 15
    tick_index: Annotated[int, Field(ge=0)]


class RiskChangedDetail(Contract):
    segment_id: SegmentId
    previous_band: RiskBand
    band: RiskBand
    score: Score
    minutes_to_flood: int | None
    reasons: Annotated[list[Reason], Field(max_length=3)]


class RiskChanged(_Event):
    """Fires only when a Segment crosses a Risk Band."""

    type: Literal["risk.changed"] = "risk.changed"
    detail: RiskChangedDetail


class ReportCreated(_Event):
    type: Literal["report.created"] = "report.created"
    detail: Report


class ReportVerified(_Event):
    type: Literal["report.verified"] = "report.verified"
    detail: Reading


class HazardDetected(_Event):
    type: Literal["hazard.detected"] = "hazard.detected"
    detail: Hazard


class SosCreated(_Event):
    type: Literal["sos.created"] = "sos.created"
    detail: Sos


class SosRankedDetail(Contract):
    ranking: list[RankedSos]


class SosRanked(_Event):
    type: Literal["sos.ranked"] = "sos.ranked"
    detail: SosRankedDetail


class ProposalCreated(_Event):
    type: Literal["proposal.created"] = "proposal.created"
    detail: Proposal


class ProposalDecidedDetail(Contract):
    proposal_id: str
    decision: Literal[ProposalStatus.APPROVED, ProposalStatus.EDITED, ProposalStatus.REJECTED]
    decided_by: str
    proposal: Annotated[Proposal, Field(description="The Proposal as approved, including any officer edits.")]


class ProposalDecided(_Event):
    type: Literal["proposal.decided"] = "proposal.decided"
    detail: ProposalDecidedDetail


class AlertSent(_Event):
    type: Literal["alert.sent"] = "alert.sent"
    detail: Alert


class PolicyDecidedDetail(Contract):
    principal: Agent
    action: Annotated[str, Field(examples=["SendAlert", "ProposeWorkOrder", "DispatchCrew", "ReadSOS"])]
    resource: str
    allowed: bool
    reason: str


class PolicyDecided(_Event):
    """Every Cedar decision, allowed or denied. Feeds the console activity feed."""

    type: Literal["policy.decided"] = "policy.decided"
    detail: PolicyDecidedDetail


class AgentActivityDetail(Contract):
    agent: Agent
    saw: str
    decided: str
    why: str


class AgentActivity(_Event):
    """One line in the console's agent activity feed."""

    type: Literal["agent.activity"] = "agent.activity"
    detail: AgentActivityDetail


Event = Annotated[
    ClockTick
    | RiskChanged
    | ReportCreated
    | ReportVerified
    | HazardDetected
    | SosCreated
    | SosRanked
    | ProposalCreated
    | ProposalDecided
    | AlertSent
    | PolicyDecided
    | AgentActivity,
    Field(discriminator="type"),
]

EVENT_TYPES = [
    ClockTick,
    RiskChanged,
    ReportCreated,
    ReportVerified,
    HazardDetected,
    SosCreated,
    SosRanked,
    ProposalCreated,
    ProposalDecided,
    AlertSent,
    PolicyDecided,
    AgentActivity,
]
