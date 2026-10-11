"""Dispatch solver (#16): which free Resource goes to which Segment, as plain greedy maths.

The Dispatcher explains and proposes these as Work Orders; it doesn't decide them.

- Needs are Segments in the `flooded` or `likely` Risk Band.
- impact = (buildings_nearby + READING_WEIGHT per Reading + SOS weight) x band weight,
  where an SOS counts for a Segment within SOS_RADIUS_M of one of its vertices and
  weighs SOS_PERSON_WEIGHT per person plus SOS_VULNERABLE_WEIGHT if anyone is
  elderly, a child or needs medical help.
- travel_minutes = haversine distance from the Resource to the Segment's first
  coordinate, driven at FLOOD_SPEED_KMH.
- score = impact / (travel_minutes + TRAVEL_OFFSET_MINUTES). The offset is the time
  to get going, and keeps a Resource already on site from scoring infinitely.
- Greedy: highest score first, each Resource used once, each Segment given at most
  one Resource. Ties break by segment_id, then resource_id, so output is deterministic.

Only pumps are assigned for now, and only to water. Tree crews belong to fallen-tree
Hazards, which aren't an input yet, so they are never sent to water.
"""

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime

from nimbus_contracts.common import GeoPoint, ResourceKind, RiskBand
from nimbus_contracts.entities import Reading, Resource, ResourceStatus, Segment, SegmentRisk, Sos

FLOOD_SPEED_KMH = 15.0  # a pump truck through flooded streets: walking pace to slow traffic
TRAVEL_OFFSET_MINUTES = 5.0
BAND_WEIGHT = {RiskBand.FLOODED: 2.0, RiskBand.LIKELY: 1.0}
READING_WEIGHT = 10.0  # each Reading is eyes-on confirmation of water
SOS_PERSON_WEIGHT = 5.0
SOS_VULNERABLE_WEIGHT = 10.0
SOS_RADIUS_M = 150.0

# Which Risk Bands each kind of Resource is sent to. Kinds not listed are never sent to water.
SENDS_TO: dict[ResourceKind, frozenset[RiskBand]] = {
    ResourceKind.PUMP: frozenset({RiskBand.FLOODED, RiskBand.LIKELY}),
}

EARTH_RADIUS_KM = 6371.0088


@dataclass(frozen=True)
class Candidate:
    resource_id: str
    segment_id: str
    rank: int  # 1 = best
    score: float
    travel_minutes: float
    buildings_affected: int
    reading_ids: tuple[str, ...]
    sos_ids: tuple[str, ...]
    numbers: dict[str, float] = field(compare=False)  # the inputs behind the score
    reason: str


def rank_work_orders(
    segments: Sequence[Segment],
    risks: Sequence[SegmentRisk],
    resources: Sequence[Resource],
    readings: Iterable[Reading] = (),
    sos: Iterable[Sos] = (),
    *,
    run_id: str,
    sim_time: datetime,
) -> list[Candidate]:
    """Ranked candidate Work Orders for this Run at `sim_time`. Pure: no I/O, no wall clock.

    Inputs from other Runs, and Readings or SOS from after `sim_time`, are ignored.
    """
    band = {r.segment_id: r.band for r in risks if r.run_id == run_id}
    needs = [s for s in segments if band.get(s.segment_id) in BAND_WEIGHT]
    free = [r for r in resources if r.run_id == run_id and r.status == ResourceStatus.FREE and r.kind in SENDS_TO]
    if not needs or not free:
        return []

    readings_by_segment: dict[str, list[Reading]] = {}
    for reading in readings:
        if reading.run_id == run_id and reading.observed_at <= sim_time:
            readings_by_segment.setdefault(reading.segment_id, []).append(reading)
    open_sos = [s for s in sos if s.run_id == run_id and s.created_at <= sim_time]

    options = []
    for segment in needs:
        seg_band = RiskBand(band[segment.segment_id])
        seg_readings = sorted(readings_by_segment.get(segment.segment_id, []), key=lambda r: r.reading_id)
        seg_sos = sorted((s for s in open_sos if _near(s.location, segment)), key=lambda s: s.sos_id)
        reading_weight = READING_WEIGHT * len(seg_readings)
        sos_weight = sum((SOS_PERSON_WEIGHT * s.people_count + (SOS_VULNERABLE_WEIGHT if _vulnerable(s) else 0) for s in seg_sos), 0.0)
        impact = (segment.buildings_nearby + reading_weight + sos_weight) * BAND_WEIGHT[seg_band]
        lon, lat = segment.geometry.coordinates[0]
        for resource in free:
            if seg_band not in SENDS_TO[ResourceKind(resource.kind)]:
                continue
            distance_km = _haversine_km(resource.location.lat, resource.location.lon, lat, lon)
            travel = distance_km / FLOOD_SPEED_KMH * 60
            score = impact / (travel + TRAVEL_OFFSET_MINUTES)
            numbers = {
                "buildings_nearby": float(segment.buildings_nearby),
                "reading_weight": reading_weight,
                "sos_weight": sos_weight,
                "band_weight": BAND_WEIGHT[seg_band],
                "impact": impact,
                "distance_km": round(distance_km, 3),
                "travel_minutes": round(travel, 1),
                "score": round(score, 3),
            }
            options.append((score, segment, seg_band, resource, travel, seg_readings, seg_sos, numbers))

    options.sort(key=lambda o: (-o[0], o[1].segment_id, o[3].resource_id))
    used_resources: set[str] = set()
    served_segments: set[str] = set()
    candidates: list[Candidate] = []
    for score, segment, seg_band, resource, travel, seg_readings, seg_sos, numbers in options:
        if resource.resource_id in used_resources or segment.segment_id in served_segments:
            continue
        used_resources.add(resource.resource_id)
        served_segments.add(segment.segment_id)
        candidates.append(
            Candidate(
                resource_id=resource.resource_id,
                segment_id=segment.segment_id,
                rank=len(candidates) + 1,
                score=round(score, 3),
                travel_minutes=round(travel, 1),
                buildings_affected=segment.buildings_nearby,
                reading_ids=tuple(r.reading_id for r in seg_readings),
                sos_ids=tuple(s.sos_id for s in seg_sos),
                numbers=numbers,
                reason=_reason(resource, segment, seg_band, travel, seg_readings, seg_sos),
            )
        )
    return candidates


def _reason(resource: Resource, segment: Segment, band: RiskBand, travel: float, readings: list[Reading], sos: list[Sos]) -> str:
    parts = [band.value, f"about {segment.buildings_nearby} buildings nearby"]
    if readings:
        parts.append("1 Reading confirms water" if len(readings) == 1 else f"{len(readings)} Readings confirm water")
    if sos:
        people = sum(s.people_count for s in sos)
        parts.append(f"{people} {'person' if people == 1 else 'people'} in {len(sos)} SOS nearby")
    parts.append("under a minute away" if travel < 1 else f"{round(travel)} min away")
    return f"Send {resource.label} to {segment.street_name or segment.segment_id}: {', '.join(parts)}."


def _vulnerable(sos: Sos) -> bool:
    return sos.flags.elderly or sos.flags.child or sos.flags.medical


def _near(point: GeoPoint, segment: Segment) -> bool:
    return any(_haversine_km(point.lat, point.lon, lat, lon) * 1000 <= SOS_RADIUS_M for lon, lat in segment.geometry.coordinates)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))
