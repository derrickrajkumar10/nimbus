"""Sentinel (#9). Done when: on fixtures, a tick produces risk.changed events and the
activity feed shows Sentinel. All local: MemoryBus, MemoryRiskStore, a fake rewrite,
and botocore's Stubber for the one test of the real Nova request."""

from datetime import UTC, datetime, timedelta, timezone

import boto3
from botocore.stub import ANY, Stubber
from nimbus_contracts.common import Agent, Reason, RiskBand
from nimbus_contracts.events import ClockTick

from common.bus import MemoryBus
from common.context import AgentContext
from common.models import AGENT_MODELS, model_id
from common.runtime import make_handler
from sentinel.core import MemoryRiskStore, run_tick
from sentinel.fixtures import FixtureScorer, _fixture_risk, load_segments
from sentinel.reasons import ReasonWriter

IST = timezone(timedelta(hours=5, minutes=30))
STORM_TIME = datetime(2023, 12, 4, 2, 0, tzinfo=IST)


def tick(index: int = 8, minutes_later: int = 0) -> ClockTick:
    return ClockTick(
        event_id=f"tick-{index}",
        run_id="replay-michaung",
        sim_time=STORM_TIME + timedelta(minutes=minutes_later),
        emitted_at=datetime(2026, 10, 11, 7, 0, tzinfo=UTC),
        source="replay-driver",
        tick_index=index,
    )


class Harness:
    """One Sentinel with a fake rewrite that records every call."""

    def __init__(self, scorer=None, rewrite=None):
        self.bus = MemoryBus()
        self.store = MemoryRiskStore()
        self.calls: list[str] = []
        self.scorer = scorer or FixtureScorer()
        self.reasons = ReasonWriter(rewrite or self._fake_rewrite)

    def _fake_rewrite(self, text: str) -> str:
        self.calls.append(text)
        return f"PLAIN: {text}"

    def run(self, t: ClockTick):
        ctx = AgentContext.for_event(Agent.SENTINEL, t, self.bus)
        return run_tick(ctx, t, segments=load_segments(), scorer=self.scorer, store=self.store, reasons=self.reasons)


def not_low_in_fixtures() -> set[str]:
    return {r.segment_id for r in _fixture_risk() if r.band != RiskBand.LOW}


def test_first_tick_flags_every_segment_above_low():
    h = Harness()
    changes = h.run(tick())

    assert {c.detail.segment_id for c in changes} == not_low_in_fixtures()
    assert all(c.detail.previous_band == RiskBand.LOW for c in changes)  # a Run starts from baseline
    assert h.bus.of_type("risk.changed") == changes


def test_same_bands_next_tick_emit_nothing():
    h = Harness()
    h.run(tick(8))
    assert h.run(tick(9, minutes_later=15)) == []
    assert len(h.bus.of_type("risk.changed")) == len(not_low_in_fixtures())  # only the first tick's


def test_band_going_down_is_a_change_too():
    h = Harness()
    h.run(tick(8))
    calmer = lambda segs, run_id, t: [  # noqa: E731
        r.model_copy(update={"band": RiskBand.LOW, "score": 10}) for r in FixtureScorer()(segs, run_id, t)
    ]
    h.scorer = calmer
    changes = h.run(tick(9, minutes_later=15))
    assert {c.detail.segment_id for c in changes} == not_low_in_fixtures()
    assert all(c.detail.band == RiskBand.LOW for c in changes)


def test_runs_do_not_share_state():
    h = Harness()
    h.run(tick())
    live = tick().model_copy(update={"run_id": "live"})
    assert len(h.run(live)) == len(not_low_in_fixtures())  # live starts from baseline too


def test_only_the_top_reason_is_rewritten():
    h = Harness()
    changes = h.run(tick())
    for c in changes:
        original = next(r for r in _fixture_risk() if r.segment_id == c.detail.segment_id).reasons
        assert c.detail.reasons[0].text == f"PLAIN: {original[0].text}"
        assert c.detail.reasons[0].code == original[0].code
        assert c.detail.reasons[1:] == original[1:]


def test_rewrites_are_cached_across_ticks():
    h = Harness()
    h.run(tick(8))
    first = list(h.calls)
    calmer = lambda segs, run_id, t: [r.model_copy(update={"band": RiskBand.LOW}) for r in FixtureScorer()(segs, run_id, t)]  # noqa: E731
    h.scorer = calmer
    h.run(tick(9, minutes_later=15))  # same reasons, bands change back
    assert h.calls == first  # no new model calls
    assert len(first) == len(set(first))  # each distinct reason rewritten once


def test_model_failure_keeps_the_original_reason():
    def broken(text):
        raise RuntimeError("Bedrock throttled")

    h = Harness(rewrite=broken)
    changes = h.run(tick())
    assert len(changes) == len(not_low_in_fixtures())  # alerts still flow
    for c in changes:
        original = next(r for r in _fixture_risk() if r.segment_id == c.detail.segment_id).reasons
        assert c.detail.reasons[0].text == original[0].text


def test_one_activity_line_per_tick_labelled_as_practice_data():
    h = Harness()
    h.run(tick(8))
    h.run(tick(9, minutes_later=15))
    first, second = h.bus.of_type("agent.activity")
    assert first.detail.agent == "sentinel"
    assert first.detail.saw.startswith("Tick 8 at 04 Dec 2023 02:00: scored 21 Segments")
    assert "practice data" in first.detail.saw
    assert first.detail.decided == f"{len(not_low_in_fixtures())} band changes"
    assert "Velachery Main Road low→flooded" in first.detail.why
    assert second.detail.decided == "No band changes"


def test_events_carry_the_ticks_run_and_storm_time():
    h = Harness()
    h.run(tick())
    for event in h.bus.events:
        assert event.run_id == "replay-michaung"
        assert event.sim_time == STORM_TIME
        assert event.source == "sentinel"


def test_handler_ignores_events_other_than_ticks():
    from sentinel.handler import handle

    bus = MemoryBus()
    other = tick().model_copy(update={"type": "risk.changed"})
    handle(AgentContext.for_event(Agent.SENTINEL, other, bus), other)
    assert bus.events == []


def test_lambda_handler_end_to_end(monkeypatch):
    # The real handler wiring, with the model rewrite faked out.
    import sentinel.handler as sh

    monkeypatch.setattr(sh.ReasonWriter, "_nova_rewrite", lambda self, text: f"PLAIN: {text}")
    sh._defaults.cache_clear()
    bus = MemoryBus()
    live = tick().model_copy(update={"run_id": "live"})  # not a Michaung Replay: practice fixtures
    payload = {"detail-type": "clock.tick", "source": "nimbus.replay-driver", "detail": live.model_dump(mode="json")}
    make_handler(Agent.SENTINEL, sh.handle, bus=bus)(payload)
    assert len(bus.of_type("risk.changed")) == len(not_low_in_fixtures())
    [activity] = bus.of_type("agent.activity")
    assert "practice data" in activity.detail.saw
    sh._defaults.cache_clear()


def _replay_ticks(monkeypatch, *ticks):
    import sentinel.handler as sh

    monkeypatch.setattr(sh.ReasonWriter, "_nova_rewrite", lambda self, text: text)
    sh._defaults.cache_clear()
    bus = MemoryBus()
    handler = make_handler(Agent.SENTINEL, sh.handle, bus=bus)
    for t in ticks:
        handler({"detail-type": "clock.tick", "source": "nimbus.replay-driver", "detail": t.model_dump(mode="json")})
    sh._defaults.cache_clear()
    return bus


def test_michaung_replay_is_scored_by_the_risk_engine(monkeypatch):
    # 4 Dec 07:45 IST is the storm's peak in the archived rain: every fixture Segment is likely.
    peak = tick(8, minutes_later=5 * 60 + 45)
    bus = _replay_ticks(monkeypatch, peak)
    [activity] = bus.of_type("agent.activity")
    assert "Michaung rain, Open-Meteo archive" in activity.detail.saw
    changes = bus.of_type("risk.changed")
    assert len(changes) == 21 and all(c.detail.band == RiskBand.LIKELY for c in changes)


def test_tick_outside_the_rain_data_is_skipped_not_retried(monkeypatch):
    from datetime import datetime as dt

    too_early = tick().model_copy(update={"sim_time": dt(2023, 11, 28, 0, 0, tzinfo=IST)})
    bus = _replay_ticks(monkeypatch, too_early)  # must not raise, or EventBridge would retry it
    assert bus.of_type("risk.changed") == []
    [activity] = bus.of_type("agent.activity")
    assert activity.detail.decided == "Skipped this tick" and "rain covers" in activity.detail.why


def test_nova_rewrite_request_uses_sentinel_settings_and_a_fresh_agent():
    session = boto3.Session(aws_access_key_id="fake", aws_secret_access_key="fake", region_name="us-east-1")
    writer = ReasonWriter(boto_session=session)
    settings = AGENT_MODELS[Agent.SENTINEL]
    reply = {
        "output": {"message": {"role": "assistant", "content": [{"text": "Heavy rain is likely to waterlog this street."}]}},
        "stopReason": "end_turn",
        "usage": {"inputTokens": 30, "outputTokens": 10, "totalTokens": 40},
        "metrics": {"latencyMs": 5},
    }
    seen = []

    import common.models as models

    real_build = models.build_agent

    def spy_build(*args, **kwargs):
        agent = real_build(*args, **kwargs)
        stub = Stubber(agent.model.client)
        stub.add_response(
            "converse",
            reply,
            {
                "modelId": model_id(Agent.SENTINEL),
                "inferenceConfig": {"maxTokens": settings.max_tokens, "temperature": settings.temperature},
                "messages": ANY,
                "system": ANY,
            },
        )
        stub.activate()
        seen.append(agent)
        return agent

    import sentinel.reasons as reasons_module

    reasons_module.build_agent = spy_build
    try:
        a = writer.plain(Reason(code="forecast_exceeds_threshold", text="32 mm forecast in 3 h against a 68 mm threshold"))
        b = writer.plain(Reason(code="antecedent_rain", text="140 mm in the last 72 h; ground is saturated"))
    finally:
        reasons_module.build_agent = real_build

    assert a.text == b.text == "Heavy rain is likely to waterlog this street."
    assert len(seen) == 2 and seen[0] is not seen[1]  # a fresh agent per rewrite, no growing history
    assert all(len(agent.messages) == 2 for agent in seen)  # one question, one answer each


def test_a_permanent_bedrock_refusal_stops_further_rewrites():
    calls = []

    def refused(text):
        calls.append(text)
        raise RuntimeError("ValidationException: An error occurred (ValidationException) when calling the Converse operation: Operation not allowed")

    h = Harness(rewrite=refused)
    changes = h.run(tick(8))
    h.run(tick(9, minutes_later=15))
    assert len(calls) == 1  # asked once, then stopped asking
    assert h.reasons.disabled
    assert len(changes) == len(not_low_in_fixtures())  # alerts still flow with the original text


def test_a_transient_failure_is_retried_next_time():
    calls = []

    def flaky(text):
        calls.append(text)
        if len(calls) == 1:
            raise RuntimeError("ThrottlingException: Rate exceeded")
        return f"PLAIN: {text}"

    h = Harness(rewrite=flaky)
    h.run(tick(8))
    assert not h.reasons.disabled
    assert len(calls) > 1
