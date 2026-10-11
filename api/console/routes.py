"""The ward console's HTTP routes (issue #8).

Every route is scoped by `run_id` and can't see another Run (ADR 0001). Officer-only routes
(`/sos`) get their JWT authorizer with issue #19; until then the API is open.
"""

import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any, Callable, Literal

from nimbus_contracts.common import RunId
from nimbus_contracts.entities import (
    Hazard,
    Proposal,
    ProposalStatus,
    Reading,
    Resource,
    SegmentRisk,
    Sos,
    WardAlertDraft,
    WorkOrder,
)
from nimbus_contracts.events import ProposalDecided, ProposalDecidedDetail
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from console.bus import Bus
from console.http import HttpError, Request, Router
from console.store import Store

log = logging.getLogger(__name__)

_RUN_ID = TypeAdapter(RunId)
_NAMESPACE = uuid.UUID("0b8e5d3a-6c1f-4f7e-8a52-3d9c1e7b4a60")  # NIMBUS console event IDs
_CURSOR = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{6}Z#.+$")
RANKED_FIELDS = ("rank", "danger_score", "reasons", "merged_sos_ids")
ACTIVITY_DEFAULT_LIMIT, ACTIVITY_MAX_LIMIT = 100, 500
RECENT_ACTIVITY = 20  # newest rows read to find the Run's storm time


class DecisionRequest(BaseModel):
    """Body of POST /proposals/{proposal_id}/decision."""

    model_config = ConfigDict(extra="forbid")

    run_id: RunId
    decision: Literal["approved", "edited", "rejected"]
    decided_by: Annotated[str, Field(min_length=1, max_length=100)]
    action: Annotated[WorkOrder | WardAlertDraft, Field(discriminator="kind")] | None = Field(
        default=None, description="The officer's edited action. Required for `edited`, forbidden otherwise."
    )


def utc_key(dt: datetime) -> str:
    """Fixed-width UTC sort-key time, as in contracts/storage.md (same format as the projector)."""
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class Console:
    def __init__(self, store: Store, bus: Bus, now: Callable[[], datetime] = lambda: datetime.now(UTC)) -> None:
        self.store, self.bus, self.now = store, bus, now
        self.router = Router()
        for path, handler in {
            "/risk": self.risk,
            "/readings": self.readings,
            "/hazards": self.hazards,
            "/resources": self.resources,
            "/sos": self.sos,
            "/proposals": self.proposals,
            "/activity": self.activity,
        }.items():
            self.router.add("GET", path, handler)
        self.router.add("POST", "/proposals/{proposal_id}/decision", self.decide)

    def handle(self, event: dict[str, Any]) -> dict[str, Any]:
        return self.router.handle(event)

    # --- reads -----------------------------------------------------------------

    @staticmethod
    def run_id(request: Request) -> str:
        raw = request.query.get("run_id")
        if not raw:
            raise HttpError(400, "run_id_required", "run_id is required: every request is scoped to one Run")
        return Console._valid_run_id(raw)

    @staticmethod
    def _valid_run_id(raw: str) -> str:
        try:
            return _RUN_ID.validate_python(raw)
        except ValidationError as error:
            raise HttpError(400, "invalid_run_id", f"run_id must be 'live' or 'replay-<name>', got {raw!r}") from error

    def _models(self, table: str, model: type[BaseModel], run_id: str) -> list[BaseModel]:
        out = []
        for row in self.store.query(table, run_id):
            try:
                out.append(model.model_validate(row))
            except ValidationError:
                log.exception("skipping a %s row that breaks the contract: %s", table, row.get("run_id"))
        return out

    def _list(self, table: str, model: type[BaseModel], request: Request) -> list[dict[str, Any]]:
        return [m.model_dump(mode="json") for m in self._models(table, model, self.run_id(request))]

    def risk(self, request: Request) -> list[dict[str, Any]]:
        return self._list("SegmentRisk", SegmentRisk, request)

    def readings(self, request: Request) -> list[dict[str, Any]]:
        return self._list("Readings", Reading, request)

    def hazards(self, request: Request) -> list[dict[str, Any]]:
        return self._list("Hazards", Hazard, request)

    def resources(self, request: Request) -> list[dict[str, Any]]:
        return self._list("Resources", Resource, request)

    def sos(self, request: Request) -> list[dict[str, Any]]:
        """Sos plus the Triage agent's ranking (rank, danger_score, reasons, merged_sos_ids) once it has one."""
        run_id = self.run_id(request)
        out = []
        for row in self.store.query("Sos", run_id):
            try:
                view = Sos.model_validate({k: v for k, v in row.items() if k in Sos.model_fields}).model_dump(mode="json")
            except ValidationError:
                log.exception("skipping an Sos row that breaks the contract")
                continue
            view |= {k: row[k] for k in RANKED_FIELDS if k in row}
            out.append(view)
        return sorted(out, key=lambda s: (s.get("rank") is None, s.get("rank", 0), s["created_at"]))

    def proposals(self, request: Request) -> list[dict[str, Any]]:
        run_id = self.run_id(request)
        status = request.query.get("status")
        if status is not None and status not in {s.value for s in ProposalStatus}:
            raise HttpError(400, "invalid_status", f"status must be one of {sorted(s.value for s in ProposalStatus)}")
        rows = self._models("Proposals", Proposal, run_id)
        wanted = [p for p in rows if status is None or p.status == status]
        return [p.model_dump(mode="json") for p in sorted(wanted, key=lambda p: (p.rank, p.proposal_id))]

    def activity(self, request: Request) -> dict[str, Any]:
        """Agent feed, oldest first. Poll with `since` set to the `cursor` of the last response."""
        run_id = self.run_id(request)
        since = request.query.get("since")
        after = self._since(since) if since else None
        try:
            limit = int(request.query.get("limit", ACTIVITY_DEFAULT_LIMIT))
        except ValueError as error:
            raise HttpError(400, "invalid_limit", "limit must be a whole number") from error
        if not 1 <= limit <= ACTIVITY_MAX_LIMIT:
            raise HttpError(400, "invalid_limit", f"limit must be between 1 and {ACTIVITY_MAX_LIMIT}")
        rows = self.store.query("Activity", run_id, after=after, limit=limit)
        items = [{k: v for k, v in row.items() if k != "emitted_at#event_id"} for row in rows]
        return {"items": items, "cursor": rows[-1]["emitted_at#event_id"] if rows else since}

    @staticmethod
    def _since(raw: str) -> str:
        if _CURSOR.match(raw):
            return raw
        try:
            moment = datetime.fromisoformat(raw)
        except ValueError as error:
            raise HttpError(400, "invalid_since", "since must be a cursor from a previous response or an ISO time") from error
        if moment.tzinfo is None:
            raise HttpError(400, "invalid_since", "since must include a timezone")
        return utc_key(moment)

    # --- the decision ----------------------------------------------------------

    def decide(self, request: Request) -> dict[str, Any]:
        """Approve, edit or reject a pending Proposal, then emit proposal.decided.

        The row is updated first, conditionally on `pending`, so a double click can't decide twice.
        The event id is derived from the Proposal, so a retry after a failed publish re-sends the
        same event and the receivers drop the duplicate.
        """
        try:
            body = DecisionRequest.model_validate(request.json())
        except ValidationError as error:
            raise HttpError(422, "invalid_decision", "the decision body is invalid", details=error.errors(include_url=False, include_context=False)) from error
        proposal_id = request.params["proposal_id"]

        existing = self._proposal(body.run_id, proposal_id)
        if body.decision == "edited":
            if body.action is None:
                raise HttpError(422, "action_required", "an edited decision needs the edited action")
            if body.action.kind != existing.action.kind:
                raise HttpError(422, "action_kind_changed", f"a {existing.action.kind} Proposal can't be edited into a {body.action.kind}")
        elif body.action is not None:
            raise HttpError(422, "action_not_allowed", "only an edited decision carries an action")

        if existing.status == ProposalStatus.PENDING:
            decided_at = self._decided_at(body.run_id, existing)
            decided = existing.model_copy(
                update={
                    "status": ProposalStatus(body.decision),
                    "decided_by": body.decided_by,
                    "decided_at": decided_at,
                    **({"action": body.action} if body.action else {}),
                }
            )
            changed = decided.model_dump(mode="json")
            values = {k: changed[k] for k in ("status", "decided_by", "decided_at", *(["action"] if body.action else []))}
            if self.store.update_proposal(body.run_id, proposal_id, values, only_if_status=ProposalStatus.PENDING.value):
                self._emit(decided)
                return changed
            existing = self._proposal(body.run_id, proposal_id)  # lost a race: look at who won

        if existing.status == body.decision and existing.decided_by == body.decided_by:
            self._emit(existing)  # a retry of the same decision: send the event again, same id
            return existing.model_dump(mode="json")
        raise HttpError(
            409, "already_decided", f"Proposal {proposal_id} is already {existing.status}",
            current_status=existing.status, decided_by=existing.decided_by,
        )

    def _proposal(self, run_id: str, proposal_id: str) -> Proposal:
        row = self.store.get("Proposals", run_id, proposal_id)
        if row is None:
            raise HttpError(404, "proposal_not_found", f"no Proposal {proposal_id} in {run_id}")
        return Proposal.model_validate(row)

    def _decided_at(self, run_id: str, proposal: Proposal) -> datetime:
        """The Run's storm time. Domain records use sim_time, never the wall clock.

        `live` runs on the wall clock. A Replay's clock is `Runs.sim_time`, written by the Replay
        Driver. The driver doesn't write that row yet, so the newest agent activity stands in: every
        event carries the storm time it was handled at. With neither (fixtures) the Proposal's own
        creation time is used. Never earlier than the Proposal was created.
        """
        clock = None
        if run_id == "live":
            clock = self.now()
        else:
            row = self.store.get("Runs", run_id)
            if row and row.get("sim_time"):
                clock = datetime.fromisoformat(str(row["sim_time"]))
            else:
                recent = self.store.query("Activity", run_id, limit=RECENT_ACTIVITY, newest_first=True)
                times = [datetime.fromisoformat(str(r["sim_time"])) for r in recent if r.get("sim_time")]
                clock = max(times) if times else None
        return max(clock, proposal.created_at) if clock else proposal.created_at

    def _emit(self, proposal: Proposal) -> None:
        assert proposal.decided_at is not None
        self.bus.publish(
            ProposalDecided(
                event_id=str(uuid.uuid5(_NAMESPACE, f"{proposal.run_id}|{proposal.proposal_id}|decided")),
                run_id=proposal.run_id,
                sim_time=proposal.decided_at,
                emitted_at=self.now(),
                source="console",
                detail=ProposalDecidedDetail(
                    proposal_id=proposal.proposal_id,
                    decision=ProposalStatus(proposal.status),
                    decided_by=proposal.decided_by or "",
                    proposal=proposal,
                ),
            )
        )
