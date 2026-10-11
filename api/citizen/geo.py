"""Which Segments does a Saved Place cover? Plain geometry, no geo library.

A Saved Place covers every Segment whose line passes within its radius. Distances use a flat
projection around the place, which is accurate to well under a metre at the scale of a ward.
"""

import math
from collections.abc import Iterable, Sequence

EARTH_M_PER_DEG_LAT = 110_540.0
EARTH_M_PER_DEG_LON_AT_EQUATOR = 111_320.0
NEAREST_FALLBACK_M = 500.0  # a place with no Segment in its radius still gets its nearest road, if this close


def _project(lat0: float, lon: float, lat: float, lon0: float) -> tuple[float, float]:
    x = (lon - lon0) * math.cos(math.radians(lat0)) * EARTH_M_PER_DEG_LON_AT_EQUATOR
    y = (lat - lat0) * EARTH_M_PER_DEG_LAT
    return x, y


def distance_to_line_m(lat: float, lon: float, coordinates: Sequence[Sequence[float]]) -> float:
    """Metres from (lat, lon) to the nearest point of a GeoJSON LineString (`[lon, lat]` pairs)."""
    points = [_project(lat, c[0], c[1], lon) for c in coordinates]  # the place is the origin
    best = math.inf
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        dx, dy = bx - ax, by - ay
        length_sq = dx * dx + dy * dy
        t = 0.0 if length_sq == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / length_sq))
        best = min(best, math.hypot(ax + t * dx, ay + t * dy))
    if len(points) == 1:
        best = math.hypot(*points[0])
    return best


def covered_segment_ids(lat: float, lon: float, radius_m: float, segments: Iterable[dict]) -> list[str]:
    """Segment ids within `radius_m`, sorted. Falls back to the nearest Segment inside 500 m."""
    measured = [(distance_to_line_m(lat, lon, s["geometry"]["coordinates"]), s["segment_id"]) for s in segments]
    inside = sorted(sid for d, sid in measured if d <= radius_m)
    if inside or not measured:
        return inside
    nearest_d, nearest_id = min(measured)
    return [nearest_id] if nearest_d <= NEAREST_FALLBACK_M else []
