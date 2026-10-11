"""Herald (#10): Place Alerts in English and Tamil, Ward Alerts only via an approved Proposal.

On risk.changed:
  - band up: alert the Segment's Subscribers, unless a place was alerted within
    COOLDOWN of storm time at the same or a higher band (no buzzing on flicker).
  - band down: all-clear, only to places this Run alerted for the Segment.
Every send goes through Cedar SendAlert. A Ward Alert (more than
WARD_ALERT_RECIPIENT_THRESHOLD recipients) is denied, so the Herald writes a
Proposal instead. On an approved proposal.decided for a ward_alert, it sends to
every Subscriber in the Run with officer_approved, since WardAlertDraft carries no
Segment.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from nimbus_contracts.common import RiskBand
from nimbus_contracts.entities import (
    WARD_ALERT_RECIPIENT_THRESHOLD,
    Alert,
    AlertScope,
    Proposal,
    ProposalStatus,
    Segment,
    WardAlertDraft,
)
from nimbus_contracts.events import AlertSent, ProposalCreated, ProposalDecided, RiskChanged

from common.context import AgentContext
from common.ids import new_id
from common.push import Push, PushSender
from herald import messages
from herald.subscribers import Subscriber, Subscribers
from sentinel.core import RiskStore

COOLDOWN = timedelta(hours=3)
BAND_ORDER = [RiskBand.LOW, RiskBand.WATCH, RiskBand.LIKELY, RiskBand.FLOODED]


def rank(band: str) -> int:
    return BAND_ORDER.index(RiskBand(band))


@dataclass
class AlertLog:
    """Last alert per (Run, place, Segment): storm time and band. In memory until stored."""

    _last: dict[tuple[str, str, str], tuple[datetime, str]] = field(default_factory=dict)

    def last(self, run_id: str, sub: Subscriber, segment_id: str) -> tuple[datetime, str] | None:
        return self._last.get((run_id, sub.place_id, segment_id))

    def record(self, run_id: str, sub: Subscriber, segment_id: str, at: datetime, band: str) -> None:
        self._last[(run_id, sub.place_id, segment_id)] = (at, band)

    def forget(self, run_id: str, sub: Subscriber, segment_id: str) -> None:
        self._last.pop((run_id, sub.place_id, segment_id), None)


def _midpoint(segment: Segment) -> tuple[float, float]:
    coords = segment.geometry.coordinates
    return sum(c[0] for c in coords) / len(coords), sum(c[1] for c in coords) / len(coords)


def _distance_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lon1, lat1, lon2, lat2 = map(math.radians, (*a, *b))
    x = (lon2 - lon1) * math.cos((lat1 + lat2) / 2)
    return 6_371_000 * math.hypot(x, lat2 - lat1)


class Herald:
    def __init__(
        self,
        *,
        segments: Sequence[Segment],
        subscribers: Subscribers,
        sender: PushSender,
        risks: RiskStore,
        log: AlertLog | None = None,
    ) -> None:
        self.segments = {s.segment_id: s for s in segments}
        self.subscribers = subscribers
        self.sender = sender
        self.risks = risks
        self.log = log or AlertLog()

    def street(self, segment_id: str) -> str:
        segment = self.segments.get(segment_id)
        return (segment.street_name if segment else None) or segment_id

    def safer_street(self, run_id: str, segment_id: str) -> str | None:
        """Nearest Segment on a different street that's currently low risk in this Run."""
        here = self.segments.get(segment_id)
        if here is None:
            return None
        current = self.risks.latest(run_id)
        candidates = [
            s
            for s in self.segments.values()
            if s.street_name
            and s.street_name != here.street_name
            and s.segment_id in current
            and current[s.segment_id].band == RiskBand.LOW
        ]
        if not candidates:
            return None
        origin = _midpoint(here)
        return min(candidates, key=lambda s: _distance_m(origin, _midpoint(s))).street_name

    # --- risk.changed ------------------------------------------------------

    def on_risk_changed(self, ctx: AgentContext, event: RiskChanged) -> None:
        d = event.detail
        street = self.street(d.segment_id)
        saw = f"{street} {d.previous_band}→{d.band}"
        subs = self.subscribers.for_segment(event.run_id, d.segment_id)
        if not subs:
            ctx.activity(saw=saw, decided="No alert", why="No Subscribers have a Saved Place on this Segment")
            return

        if rank(d.band) < rank(d.previous_band):
            self._all_clear(ctx, event, subs, saw)
            return

        due = [s for s in subs if self._due(event, s)]
        if not due:
            ctx.activity(saw=saw, decided="No alert", why=f"All {len(subs)} places were alerted within {COOLDOWN.seconds // 3600} h at this band or higher")
            return

        message = messages.risk_alert(street, RiskBand(d.band), d.minutes_to_flood, self.safer_street(event.run_id, d.segment_id))
        self._send_or_propose(ctx, event, due, message, [d.segment_id], d.band, saw)

    def _due(self, event: RiskChanged, sub: Subscriber) -> bool:
        last = self.log.last(event.run_id, sub, event.detail.segment_id)
        if last is None:
            return True
        at, band = last
        return event.sim_time - at >= COOLDOWN or rank(event.detail.band) > rank(band)

    def _all_clear(self, ctx: AgentContext, event: RiskChanged, subs: list[Subscriber], saw: str) -> None:
        segment_id = event.detail.segment_id
        alerted = [s for s in subs if self.log.last(event.run_id, s, segment_id)]
        if not alerted:
            ctx.activity(saw=saw, decided="No all-clear", why="No place was alerted for this Segment in this Run")
            return
        sent = self._send(ctx, event.run_id, alerted, messages.all_clear(self.street(segment_id)), [segment_id], AlertScope.PLACE, approved=False, proposal_id=None, band=event.detail.band, saw=saw)
        if sent:
            for sub in alerted:
                self.log.forget(event.run_id, sub, segment_id)

    def _send_or_propose(self, ctx, event, subs, message, segment_ids, band, saw) -> None:
        if len(subs) > WARD_ALERT_RECIPIENT_THRESHOLD:
            # Ask Cedar first so the denial shows in the feed, then hold it as a Proposal.
            decision = ctx.cedar_check(
                "SendAlert",
                f'Alert::"{new_id("al", event.sim_time)}"',
                resource_attrs={"scope": AlertScope.PLACE.value, "recipient_count": len(subs)},
            )
            if not decision.allowed:
                self._propose(ctx, event.run_id, message, len(subs), saw, decision.reason)
                return
        if self._send(ctx, event.run_id, subs, message, segment_ids, AlertScope.PLACE, approved=False, proposal_id=None, band=band, saw=saw):
            for sub in subs:
                self.log.record(event.run_id, sub, segment_ids[0], event.sim_time, band)

    def _propose(self, ctx: AgentContext, run_id: str, message: messages.Message, recipients: int, saw: str, why: str) -> None:
        final = messages.for_run(message, run_id)
        proposal = Proposal(
            proposal_id=new_id("pr", ctx.sim_time),
            run_id=run_id,
            proposed_by=ctx.agent,
            created_at=ctx.sim_time,
            rank=1,
            reason=f"Ward Alert to {recipients} Subscribers needs an officer's approval: {final.body['en']}",
            action=WardAlertDraft(message_en=final.body["en"], message_ta=final.body["ta"], recipient_count=recipients),
        )
        ctx.publish(ProposalCreated, proposal)
        ctx.activity(saw=saw, decided=f"Held a Ward Alert for {recipients} Subscribers for officer approval", why=why)

    # --- proposal.decided --------------------------------------------------

    def on_proposal_decided(self, ctx: AgentContext, event: ProposalDecided) -> None:
        d = event.detail
        draft = d.proposal.action
        if draft.kind != "ward_alert" or d.decision == ProposalStatus.REJECTED:
            return
        subs = self.subscribers.all_in_run(event.run_id)
        saw = f"Officer {d.decided_by} {d.decision} Ward Alert {d.proposal_id}"
        if not subs:
            ctx.activity(saw=saw, decided="No Ward Alert sent", why="No Subscribers in this Run")
            return
        # The draft's text includes any officer edits (and the [REPLAY] prefix it was proposed with).
        message = messages.Message(
            title={"en": "Ward alert", "ta": "வார்டு எச்சரிக்கை"},
            body={"en": draft.message_en, "ta": draft.message_ta},
        )
        self._send(ctx, event.run_id, subs, message, [], AlertScope.WARD, approved=True, proposal_id=d.proposal_id, band=None, saw=saw)

    # --- sending -----------------------------------------------------------

    def _send(self, ctx, run_id, subs, message, segment_ids, scope, *, approved, proposal_id, band, saw) -> bool:
        alert_id = new_id("al", ctx.sim_time)
        devices = tuple(dict.fromkeys(s.device_id for s in subs))
        decision = ctx.cedar_check(
            "SendAlert",
            f'Alert::"{alert_id}"',
            resource_attrs={"scope": scope.value, "recipient_count": len(devices)},
            context={"officer_approved": approved},
        )
        if not decision.allowed:
            ctx.activity(saw=saw, decided="Alert blocked", why=decision.reason)
            return False

        final = messages.for_run(message, run_id)
        data = {"alert_id": alert_id, "run_id": run_id}
        if segment_ids:
            data["segment_id"] = segment_ids[0]
        if band:
            data["band"] = str(band)
        result = self.sender.send(Push(run_id=run_id, device_ids=devices, title=final.title, body=final.body, data=data))

        ctx.publish(
            AlertSent,
            Alert(
                alert_id=alert_id,
                run_id=run_id,
                scope=scope,
                sent_at=ctx.sim_time,
                segment_ids=list(segment_ids),
                recipient_count=len(devices),
                message_en=final.body["en"],
                message_ta=final.body["ta"],
                proposal_id=proposal_id,
            ),
        )
        ctx.activity(
            saw=saw,
            decided=f"Sent {'a Ward Alert' if scope == AlertScope.WARD else 'an alert'} to {result.sent} of {len(devices)} devices",
            why=decision.reason,
        )
        return True
