"""Hourly rain for the risk engine, keyed by storm time.

`RainSeries` holds the rain at one point (the whole Ward shares it for now) as
hour-end timestamp -> mm in the hour ending then, which is how Open-Meteo reports
hourly precipitation. Rain within an hour is taken as evenly spread, so 15-minute
ticks see it build up smoothly.
"""

import json
from collections.abc import Mapping
from datetime import datetime, timedelta
from functools import cache
from pathlib import Path

HOUR = timedelta(hours=1)
MICHAUNG_RAIN = Path(__file__).resolve().parent / "michaung_rain.json"


class RainSeries:
    def __init__(self, hourly: Mapping[datetime, float]) -> None:
        if not hourly:
            raise ValueError("a RainSeries needs at least one hour of rain")
        if any(t.tzinfo is None for t in hourly):
            raise ValueError("rain timestamps must carry a UTC offset")
        self._hours = sorted(hourly.items())
        self.start = self._hours[0][0] - HOUR
        self.end = self._hours[-1][0]

    def covers(self, start: datetime, end: datetime) -> bool:
        return self.start <= start and end <= self.end

    def between(self, start: datetime, end: datetime) -> float:
        """Rain (mm) that fell after `start`, up to and including `end`."""
        total = 0.0
        for hour_end, mm in self._hours:
            overlap = min(end, hour_end) - max(start, hour_end - HOUR)
            if overlap > timedelta(0):
                total += mm * (overlap / HOUR)
        return total


@cache
def load_michaung_rain() -> RainSeries:
    """Open-Meteo archive rain for Velachery, 28 Nov to 6 Dec 2023, committed next to this file."""
    data = json.loads(MICHAUNG_RAIN.read_text())
    return RainSeries({datetime.fromisoformat(t): float(mm) for t, mm in data["hourly"].items()})
