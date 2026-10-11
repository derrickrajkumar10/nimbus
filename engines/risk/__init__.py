"""F2 risk engine. Standard library and nimbus_contracts only: it is bundled into the Sentinel's Lambda."""

from collections.abc import Sequence
from datetime import datetime

from nimbus_contracts.entities import Segment, SegmentRisk

from risk.rain import RainSeries, load_michaung_rain
from risk.score import score_segments

__all__ = ["MichaungScorer", "RainSeries", "load_michaung_rain", "score_segments"]


class MichaungScorer:
    """The Sentinel's Scorer for the Michaung Replay: (segments, run_id, sim_time) -> list[SegmentRisk]."""

    label = "Michaung rain, Open-Meteo archive"

    def __init__(self, rain: RainSeries | None = None) -> None:
        self._rain = rain

    def __call__(self, segments: Sequence[Segment], run_id: str, sim_time: datetime) -> list[SegmentRisk]:
        return score_segments(segments, self._rain or load_michaung_rain(), run_id, sim_time)
