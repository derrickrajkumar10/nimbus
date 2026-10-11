"""Practice data from contracts/fixtures/, until F1 Segments and the F2 risk engine (#4) land.

FixtureScorer replays the single fixture snapshot (Michaung, 4 Dec 2023 02:00 IST)
for whatever tick it's given. Its `label` shows up in the Sentinel's activity line,
so the feed never presents fixture risk as real scoring.
"""

import json
from collections.abc import Sequence
from datetime import datetime
from functools import cache
from pathlib import Path

from nimbus_contracts.entities import Segment, SegmentRisk

_HERE = Path(__file__).resolve()
# In the Lambda bundle the fixtures sit next to the agent packages; in the repo, under ../contracts.
_CANDIDATES = (_HERE.parents[1] / "contracts" / "fixtures", _HERE.parents[2] / "contracts" / "fixtures")
FIXTURES = next((p for p in _CANDIDATES if p.is_dir()), _CANDIDATES[-1])


@cache
def load_segments() -> tuple[Segment, ...]:
    return tuple(Segment.model_validate(row) for row in json.loads((FIXTURES / "segments.json").read_text()))


@cache
def _fixture_risk() -> tuple[SegmentRisk, ...]:
    return tuple(SegmentRisk.model_validate(row) for row in json.loads((FIXTURES / "risk.json").read_text()))


class FixtureScorer:
    label = "practice data, risk engine #4 not connected"

    def __call__(self, segments: Sequence[Segment], run_id: str, sim_time: datetime) -> list[SegmentRisk]:
        wanted = {s.segment_id for s in segments}
        return [
            risk.model_copy(update={"run_id": run_id, "sim_time": sim_time})
            for risk in _fixture_risk()
            if risk.segment_id in wanted
        ]
