import json
from datetime import UTC, datetime, timedelta, timezone

import pytest
from nimbus_contracts.common import Agent
from nimbus_contracts.events import AgentActivity, AgentActivityDetail

from common.keys import utc_key

IST = timezone(timedelta(hours=5, minutes=30))


def test_fixture_storm_time_in_ist_becomes_utc_z():
    assert utc_key(datetime(2023, 12, 4, 2, 0, tzinfo=IST)) == "2023-12-03T20:30:00.000000Z"


def test_naive_times_are_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        utc_key(datetime(2023, 12, 4, 2, 0))


def test_text_order_matches_time_order_across_offsets_and_fractions():
    times = [
        datetime(2023, 12, 4, 2, 0, tzinfo=IST),  # 20:30:00 UTC on the 3rd
        datetime(2023, 12, 3, 20, 30, 0, 500000, tzinfo=UTC),  # half a second later
        datetime(2023, 12, 3, 20, 30, 1, tzinfo=UTC),
        datetime(2023, 12, 4, 2, 0, 2, tzinfo=IST),
    ]
    assert sorted(times, key=utc_key) == sorted(times)
    assert sorted(utc_key(t) for t in times) == [utc_key(t) for t in sorted(times)]


def test_event_json_times_would_sort_wrongly_as_keys():
    # Why utc_key exists: the contract's JSON drops a zero fraction.
    def emitted(dt):
        event = AgentActivity(
            event_id="e", run_id="live", sim_time=dt, emitted_at=dt, source="herald",
            detail=AgentActivityDetail(agent=Agent.HERALD, saw="a", decided="b", why="c"),
        )
        return json.loads(event.model_dump_json())["emitted_at"]

    earlier = datetime(2026, 10, 11, 7, 0, 0, tzinfo=UTC)
    later = earlier + timedelta(milliseconds=500)
    assert emitted(later) < emitted(earlier)  # wrong order as text
    assert utc_key(earlier) < utc_key(later)  # right order
