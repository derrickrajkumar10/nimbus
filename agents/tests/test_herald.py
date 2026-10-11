"""Herald (#10). Local only: MemoryBus, MemoryPushSender (no phones, no Firebase, no AWS)."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from nimbus_contracts.common import Agent, Reason, RiskBand
from nimbus_contracts.entities import ProposalStatus
from nimbus_contracts.events import ProposalDecided, ProposalDecidedDetail, RiskChanged, RiskChangedDetail

from common.bus import MemoryBus
from common.context import AgentContext
from common.ids import new_id, ulid
from common.push import MemoryPushSender, PushError
from herald import messages
from herald.core import Herald
from herald.subscribers import MemorySubscribers, Subscriber, practice_subscribers
from sentinel.core import MemoryRiskStore, run_tick
from sentinel.fixtures import FixtureScorer, load_segments
from sentinel.reasons import ReasonWriter
from tests.test_sentinel import tick

IST = timezone(timedelta(hours=5, minutes=30))
T0 = datetime(2023, 12, 4, 2, 0, tzinfo=IST)
FLOODED_VMR = "27480309-1"  # Velachery Main Road, flooded in fixtures
LIKELY_VMR = "27480309-4"  # Velachery Main Road, likely, 30 min to flood


class World:
    """Sentinel and Herald sharing one bus and risk store, like the deployed system."""

    def __init__(self, subscribers=None, run_id="replay-michaung"):
        self.bus = MemoryBus()
        self.risks = MemoryRiskStore()
        self.sender = MemoryPushSender()
        self.run_id = run_id
        self.herald = Herald(
            segments=load_segments(), subscribers=subscribers or practice_subscribers(), sender=self.sender, risks=self.risks
        )

    def ctx(self, agent, event):
        return AgentContext.for_event(agent, event, self.bus)

    def sentinel_tick(self, index=8, minutes_later=0):
        t = tick(index, minutes_later).model_copy(update={"run_id": self.run_id})
        changes = run_tick(
            self.ctx(Agent.SENTINEL, t), t, segments=load_segments(), scorer=FixtureScorer(), store=self.risks,
            reasons=ReasonWriter(lambda text: text),
        )
        for change in changes:
            self.herald.on_risk_changed(self.ctx(Agent.HERALD, change), change)
        return changes

    def risk_changed(self, segment_id, before, after, at=T0, minutes=60):
        event = RiskChanged(
            event_id=new_id("ev", at), run_id=self.run_id, sim_time=at, emitted_at=datetime.now(UTC), source="sentinel",
            detail=RiskChangedDetail(
                segment_id=segment_id, previous_band=before, band=after, score=80, minutes_to_flood=minutes,
                reasons=[Reason(code="forecast_exceeds_threshold", text="49 mm forecast in 3 h against a 89 mm threshold")],
            ),
        )
        self.herald.on_risk_changed(self.ctx(Agent.HERALD, event), event)
        return event

    def decide(self, proposal, decision=ProposalStatus.APPROVED, at=T0):
        event = ProposalDecided(
            event_id=new_id("ev", at), run_id=self.run_id, sim_time=at, emitted_at=datetime.now(UTC), source="console",
            detail=ProposalDecidedDetail(proposal_id=proposal.proposal_id, decision=decision, decided_by="officer-priya", proposal=proposal),
        )
        self.herald.on_proposal_decided(self.ctx(Agent.HERALD, event), event)


def crowd(n, segment_id=LIKELY_VMR, run_id="replay-michaung"):
    subs = MemorySubscribers()
    for i in range(n):
        subs.add(run_id, segment_id, Subscriber(f"dev-{i}", f"place-{i}"))
    return subs


# --- the M1 path ----------------------------------------------------------


def test_fixture_tick_alerts_the_demo_phones_in_tamil_and_english():
    w = World()
    w.sentinel_tick()

    by_device = {d: p for p in w.sender.sent for d in p.device_ids}
    assert set(by_device) == {"demo-phone-1", "demo-phone-2", "demo-phone-3"}
    flooded = by_device["demo-phone-1"]
    assert flooded.title["ta"] == "[REPLAY] வெள்ள எச்சரிக்கை: Velachery Main Road"
    assert flooded.body["ta"].startswith("[REPLAY] சரிபார்க்கப்பட்ட தகவல்களின்படி")
    assert "waterlogged now" in flooded.body["en"]
    likely = by_device["demo-phone-3"]
    assert "likely waterlogged within the hour" in likely.body["en"]

    sent = w.bus.of_type("alert.sent")
    assert len(sent) == 2 and all(e.detail.scope == "place" for e in sent)
    assert {e.detail.segment_ids[0] for e in sent} == {FLOODED_VMR, LIKELY_VMR}
    assert all(e.detail.message_ta.startswith("[REPLAY] ") for e in sent)
    herald_checks = [e for e in w.bus.of_type("policy.decided") if e.detail.principal == "herald"]
    assert herald_checks and all(e.detail.allowed for e in herald_checks)


def test_safer_street_is_a_different_low_risk_street():
    w = World()
    w.sentinel_tick()
    safer = w.herald.safer_street(w.run_id, LIKELY_VMR)
    assert safer and safer != "Velachery Main Road"
    current = w.risks.latest(w.run_id)
    low_streets = {s.street_name for s in load_segments() if current[s.segment_id].band == RiskBand.LOW}
    assert safer in low_streets
    assert f"to {safer} now" in next(p for p in w.sender.sent if "demo-phone-3" in p.device_ids).body["en"]


def test_live_run_has_no_replay_prefix():
    subs = MemorySubscribers()
    subs.add("live", LIKELY_VMR, Subscriber("dev-live", "place-1"))
    w = World(subscribers=subs, run_id="live")
    w.risk_changed(LIKELY_VMR, RiskBand.WATCH, RiskBand.LIKELY)
    [push] = w.sender.sent
    assert not push.title["en"].startswith("[REPLAY]") and not push.body["ta"].startswith("[REPLAY]")


# --- Ward Alerts: Cedar holds them until an officer approves ---------------


def test_over_100_recipients_becomes_a_proposal_not_a_push():
    w = World(subscribers=crowd(150))
    w.risk_changed(LIKELY_VMR, RiskBand.WATCH, RiskBand.LIKELY)

    assert w.sender.sent == []
    assert w.bus.of_type("alert.sent") == []
    [denied] = [e for e in w.bus.of_type("policy.decided") if not e.detail.allowed]
    assert "ward-alerts-need-approval" in denied.detail.reason
    [created] = w.bus.of_type("proposal.created")
    proposal = created.detail
    assert proposal.proposed_by == "herald" and proposal.status == "pending"
    assert proposal.action.kind == "ward_alert" and proposal.action.recipient_count == 150
    assert proposal.action.message_ta.startswith("[REPLAY] ")
    assert proposal.proposal_id.startswith("pr-")
    feed = w.bus.of_type("agent.activity")[-1].detail
    assert feed.decided == "Held a Ward Alert for 150 Subscribers for officer approval"


def test_approved_ward_alert_goes_out_with_officer_approval():
    w = World(subscribers=crowd(150))
    w.risk_changed(LIKELY_VMR, RiskBand.WATCH, RiskBand.LIKELY)
    proposal = w.bus.of_type("proposal.created")[0].detail

    w.decide(proposal, ProposalStatus.APPROVED, at=T0 + timedelta(minutes=5))

    [push] = w.sender.sent
    assert len(push.device_ids) == 150
    assert push.body["ta"] == proposal.action.message_ta  # not double-prefixed
    assert push.title["en"] == "[REPLAY] Ward alert"
    [sent] = w.bus.of_type("alert.sent")
    assert sent.detail.scope == "ward" and sent.detail.proposal_id == proposal.proposal_id
    assert w.bus.of_type("policy.decided")[-1].detail.allowed is True


def test_rejected_ward_alert_sends_nothing():
    w = World(subscribers=crowd(150))
    w.risk_changed(LIKELY_VMR, RiskBand.WATCH, RiskBand.LIKELY)
    w.decide(w.bus.of_type("proposal.created")[0].detail, ProposalStatus.REJECTED)
    assert w.sender.sent == []


def test_exactly_100_recipients_is_still_a_place_alert():
    w = World(subscribers=crowd(100))
    w.risk_changed(LIKELY_VMR, RiskBand.WATCH, RiskBand.LIKELY)
    assert len(w.sender.sent) == 1 and w.bus.of_type("proposal.created") == []


# --- anti-fatigue ----------------------------------------------------------


def one_place():
    subs = MemorySubscribers()
    subs.add("replay-michaung", LIKELY_VMR, Subscriber("dev-1", "place-1"))
    return subs


def test_no_repeat_within_3_hours_at_the_same_band():
    w = World(subscribers=one_place())
    w.risk_changed(LIKELY_VMR, RiskBand.WATCH, RiskBand.LIKELY, at=T0)
    w.risk_changed(LIKELY_VMR, RiskBand.LOW, RiskBand.LIKELY, at=T0 + timedelta(hours=2))  # flicker back up
    assert len(w.sender.sent) == 1
    assert "within 3 h" in w.bus.of_type("agent.activity")[-1].detail.why


def test_repeat_allowed_after_3_hours():
    w = World(subscribers=one_place())
    w.risk_changed(LIKELY_VMR, RiskBand.WATCH, RiskBand.LIKELY, at=T0)
    w.risk_changed(LIKELY_VMR, RiskBand.WATCH, RiskBand.LIKELY, at=T0 + timedelta(hours=3))
    assert len(w.sender.sent) == 2


def test_getting_worse_within_3_hours_still_alerts():
    w = World(subscribers=one_place())
    w.risk_changed(LIKELY_VMR, RiskBand.LOW, RiskBand.WATCH, at=T0)
    w.risk_changed(LIKELY_VMR, RiskBand.WATCH, RiskBand.LIKELY, at=T0 + timedelta(minutes=30))
    assert len(w.sender.sent) == 2


def test_all_clear_only_to_places_that_were_alerted():
    subs = one_place()
    subs.add("replay-michaung", LIKELY_VMR, Subscriber("dev-late", "place-late"))
    w = World(subscribers=subs)
    w.risk_changed(LIKELY_VMR, RiskBand.WATCH, RiskBand.LIKELY, at=T0)
    w.sender.sent.clear()
    subs.add("replay-michaung", LIKELY_VMR, Subscriber("dev-new", "place-new"))  # subscribed after the alert

    w.risk_changed(LIKELY_VMR, RiskBand.LIKELY, RiskBand.LOW, at=T0 + timedelta(hours=1))
    [clear] = w.sender.sent
    assert set(clear.device_ids) == {"dev-1", "dev-late"}
    assert clear.title["en"] == "[REPLAY] All clear: Velachery Main Road"

    w.risk_changed(LIKELY_VMR, RiskBand.WATCH, RiskBand.LOW, at=T0 + timedelta(hours=2))
    assert len(w.sender.sent) == 1  # no second all-clear


def test_no_subscribers_means_no_alert_but_a_feed_line():
    w = World(subscribers=MemorySubscribers())
    w.risk_changed(LIKELY_VMR, RiskBand.WATCH, RiskBand.LIKELY)
    assert w.sender.sent == []
    assert w.bus.of_type("agent.activity")[-1].detail.decided == "No alert"


def test_failed_push_is_not_recorded_as_sent():
    class Broken:
        def send(self, push):
            raise PushError("send-push failed")

    w = World(subscribers=one_place())
    w.herald.sender = Broken()
    with pytest.raises(PushError):
        w.risk_changed(LIKELY_VMR, RiskBand.WATCH, RiskBand.LIKELY)
    assert w.bus.of_type("alert.sent") == []
    w.herald.sender = w.sender
    w.risk_changed(LIKELY_VMR, RiskBand.WATCH, RiskBand.LIKELY)  # EventBridge retry
    assert len(w.sender.sent) == 1


# --- wording -----------------------------------------------------------------


@pytest.mark.parametrize(
    "minutes, en, ta",
    [(30, "within the hour", "ஒரு மணி நேரத்திற்குள்"), (120, "in about 2 hours", "சுமார் 2 மணி நேரத்தில்"), (None, "soon", "விரைவில்")],
)
def test_likely_wording_says_when(minutes, en, ta):
    m = messages.risk_alert("LIC Colony Main Road", RiskBand.LIKELY, minutes, "Ram Nagar Main Road")
    assert f"likely waterlogged {en}" in m.body["en"]
    assert ta in m.body["ta"]
    assert m.body["en"].endswith("Move your two-wheeler to Ram Nagar Main Road now.")


def test_without_a_safer_street_it_says_higher_ground():
    m = messages.risk_alert("LIC Colony Main Road", RiskBand.WATCH, 120, None)
    assert "to higher ground" in m.body["en"] and "மேடான இடத்திற்கு" in m.body["ta"]


def test_predictions_never_say_the_street_is_flooded_now():
    for band in (RiskBand.WATCH, RiskBand.LIKELY):
        m = messages.risk_alert("X", band, 60, None)
        assert "now." not in m.body["en"].split(".")[0] and "waterlogged now" not in m.body["en"]


def test_ids_sort_by_time_and_carry_a_prefix():
    a, b = new_id("al", T0), new_id("al", T0 + timedelta(seconds=1))
    assert a.startswith("al-") and len(ulid(T0)) == 26 and a < b
