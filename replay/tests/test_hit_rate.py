"""Hit Rate on the Michaung Replay, offline: the risk engine over fixture Segments."""

from datetime import datetime

import hit_rate
from risk import MichaungScorer


def test_some_segment_is_likely_before_8am_on_4_december():
    result = hit_rate.first_crossings(hit_rate.load_segments(), MichaungScorer())

    first_likely = min(c.likely for c in result.crossings.values() if c.likely)
    assert first_likely < datetime.fromisoformat("2023-12-04T08:00:00+05:30")
