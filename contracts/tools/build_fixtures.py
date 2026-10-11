"""Build fixture data from a real Velachery OSM extract so every lane can start before F1 exists.

Geometry, Segment IDs, street names and building counts are real. Terrain numbers,
thresholds, risk, Readings and Proposals are made up and deterministic.

    uv run python tools/build_fixtures.py
"""

import json
import math
import random
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

from nimbus_contracts.common import GeoPoint, LineString, Reason, RiskBand
from nimbus_contracts.entities import (
    Hazard,
    HazardStatus,
    Passability,
    Proposal,
    Reading,
    Resource,
    ResourceStatus,
    Segment,
    SegmentRisk,
    Sos,
    TerrainFactors,
    VulnerabilityFlags,
    WorkOrder,
)
from nimbus_contracts.routes import RouteRequest, RouteResponse, RouteStatus
from nimbus_contracts.rules import band_for_score
from nimbus_contracts.segments import OsmWay, split_ways

ROOT = Path(__file__).resolve().parent.parent
OSM = ROOT / "tools" / "velachery-sample.osm"
OUT = ROOT / "fixtures"

ROAD_CLASSES = {"primary", "secondary", "tertiary", "residential", "unclassified"}
STREETS = [
    "Velachery Main Road",
    "Ram Nagar Main Road",
    "Vijayanagar 1st Main Road",
    "Sarathy Nagar 1st Main Road",
    "Tansi Nagar 1st Street",
    "LIC Colony Main Road",
]
PER_STREET = 4
RUN = "replay-michaung"
IST = timezone(timedelta(hours=5, minutes=30))
SIM_TIME = datetime(2023, 12, 4, 2, 0, tzinfo=IST)


def haversine_m(a, b):
    lon1, lat1, lon2, lat2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6_371_000 * math.asin(math.sqrt(h))


def load_osm():
    root = ET.parse(OSM).getroot()
    nodes = {int(n.get("id")): (float(n.get("lon")), float(n.get("lat"))) for n in root.iter("node")}
    roads, names, buildings = [], {}, []
    for w in root.iter("way"):
        tags = {t.get("k"): t.get("v") for t in w.iter("tag")}
        refs = [int(nd.get("ref")) for nd in w.iter("nd")]
        if tags.get("highway") in ROAD_CLASSES and all(r in nodes for r in refs):
            roads.append(OsmWay(int(w.get("id")), refs))
            names[int(w.get("id"))] = tags.get("name")
        elif "building" in tags and refs and all(r in nodes for r in refs):
            pts = [nodes[r] for r in refs]
            buildings.append((sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)))
    return nodes, roads, names, buildings


def build_segments():
    nodes, roads, names, buildings = load_osm()
    pieces = [p for p in split_ways(roads) if names[p.osm_way_id] in STREETS]
    pieces.sort(key=lambda p: (STREETS.index(names[p.osm_way_id]), p.osm_way_id, int(p.segment_id.split("-")[1])))
    segments, per_street = [], {}
    for p in pieces:
        coords = [nodes[n] for n in p.node_ids]
        length = sum(haversine_m(a, b) for a, b in zip(coords, coords[1:]))
        name = names[p.osm_way_id]
        if length < 5 or per_street.get(name, 0) >= PER_STREET:
            continue
        per_street[name] = per_street.get(name, 0) + 1
        mid = coords[len(coords) // 2]
        rng = random.Random(p.segment_id)
        segments.append(
            Segment(
                segment_id=p.segment_id,
                osm_way_id=p.osm_way_id,
                street_name=names[p.osm_way_id],
                ward="velachery",
                geometry=LineString(coordinates=[[round(x, 7), round(y, 7)] for x, y in coords]),
                length_m=round(length, 1),
                baseline_threshold_mm=round(rng.uniform(25, 90), 1),
                terrain=TerrainFactors(
                    depression_depth_m=round(rng.uniform(0, 1.5), 2),
                    catchment_area_m2=round(rng.uniform(5_000, 400_000)),
                    distance_to_water_m=round(rng.uniform(50, 1_500)),
                ),
                buildings_nearby=sum(1 for b in buildings if haversine_m(mid, b) <= 100),
            )
        )
    return segments


def midpoint(segment):
    lon, lat = segment.geometry.coordinates[len(segment.geometry.coordinates) // 2]
    return GeoPoint(lat=lat, lon=lon)


def flooded_segment(segments):
    """The demo's pump scene: the busiest Velachery Main Road Segment is knee-deep."""
    return max((s for s in segments if s.street_name == "Velachery Main Road"), key=lambda s: s.buildings_nearby)


def build_risk(segments):
    risk, flooded = [], flooded_segment(segments)
    for s in segments:
        rng = random.Random(f"risk-{s.segment_id}")
        if s == flooded:
            band, score, minutes = RiskBand.FLOODED, 92, 0
        else:
            score = rng.randint(5, 95)
            band = band_for_score(score)
            minutes = None if band == RiskBand.LOW else rng.choice([30, 60, 90, 120, 180])
        reasons = [Reason(code="forecast_exceeds_threshold", text=f"{rng.randint(20, 60)} mm forecast in 3 h against a {s.baseline_threshold_mm:.0f} mm threshold")]
        if band in (RiskBand.LIKELY, RiskBand.FLOODED):
            reasons.append(Reason(code="antecedent_rain", text="140 mm in the last 72 h; ground is saturated"))
        if band == RiskBand.FLOODED:
            reasons.insert(0, Reason(code="nearby_reading", text="Knee-deep Reading from 3 merged Reports"))
        risk.append(
            SegmentRisk(
                run_id=RUN,
                segment_id=s.segment_id,
                sim_time=SIM_TIME,
                score=score,
                band=band,
                minutes_to_flood=minutes,
                reasons=reasons[:3],
                flood_threshold_mm=s.baseline_threshold_mm,
            )
        )
    return risk


def build_scene(segments):
    flooded = flooded_segment(segments)
    side_street = next(s for s in segments if s.street_name == "Ram Nagar Main Road")
    reading = Reading(
        reading_id="rd-0001",
        run_id=RUN,
        segment_id=flooded.segment_id,
        observed_at=SIM_TIME - timedelta(minutes=10),
        depth="knee",
        reference_object="tyre",
        confidence=0.82,
        passable=Passability(two_wheeler=False, car=False, ambulance=True),
        report_ids=["rp-0001", "rp-0002", "rp-0003"],
        hazards_seen=["open_manhole"],
    )
    hazard = Hazard(
        hazard_id="hz-0001",
        run_id=RUN,
        hazard_class="open_manhole",
        location=midpoint(flooded),
        owner="corporation",
        status=HazardStatus.OPEN,
        detected_at=reading.observed_at,
        source_report_id="rp-0002",
    )
    resources = [
        Resource(resource_id="rs-pump-1", run_id=RUN, kind="pump", label="Pump 1", status=ResourceStatus.WORKING, location=midpoint(segments[5])),
        Resource(resource_id="rs-pump-2", run_id=RUN, kind="pump", label="Pump 2", status=ResourceStatus.FREE, location=midpoint(segments[-1])),
        Resource(resource_id="rs-tree-1", run_id=RUN, kind="tree_crew", label="Tree crew 1", status=ResourceStatus.FREE, location=midpoint(segments[-2])),
    ]
    proposal = Proposal(
        proposal_id="pr-0001",
        run_id=RUN,
        proposed_by="dispatcher",
        created_at=SIM_TIME,
        rank=1,
        reason=f"Send Pump 2 to {flooded.street_name}: 3 Reports merged into a knee-deep Reading, about {flooded.buildings_nearby} buildings nearby.",
        action=WorkOrder(resource_id="rs-pump-2", segment_id=flooded.segment_id, buildings_affected=flooded.buildings_nearby, reading_ids=[reading.reading_id]),
    )
    sos = Sos(
        sos_id="sos-0001",
        run_id=RUN,
        reporter_id="install-demo-2",
        created_at=SIM_TIME - timedelta(minutes=5),
        location=midpoint(side_street),
        people_count=3,
        flags=VulnerabilityFlags(elderly=True),
    )
    return {"readings": [reading], "hazards": [hazard], "resources": resources, "proposals": [proposal], "sos": [sos]}


def build_routes(segments):
    """Two answers for a two-wheeler: a detour around the flooded Segment, and no safe route."""
    flooded = flooded_segment(segments)
    bystreet = [s for s in segments if s.street_name == "Ram Nagar Main Road"][:2]
    origin, destination = midpoint(bystreet[0]), midpoint(bystreet[-1])
    coords = [c for s in bystreet for c in s.geometry.coordinates]
    metres = sum(haversine_m(a, b) for a, b in zip(coords, coords[1:]))
    two_wheeler_m_per_s = 25 / 3.6
    requests = [
        RouteRequest(run_id=RUN, origin=origin, destination=destination, vehicle="two_wheeler"),
        RouteRequest(run_id=RUN, origin=origin, destination=midpoint(flooded), vehicle="car"),
    ]
    responses = [
        RouteResponse(
            run_id=RUN,
            status=RouteStatus.OK,
            geometry=LineString(coordinates=coords),
            distance_m=round(metres, 1),
            duration_s=round(metres / two_wheeler_m_per_s),
            avoided_segment_ids=[flooded.segment_id],
            avoided_hazard_ids=["hz-0001"],  # the open manhole in the flooded Segment
            reason=f"Avoids {flooded.street_name}, reported knee-deep.",
        ),
        RouteResponse(
            run_id=RUN,
            status=RouteStatus.NO_SAFE_ROUTE,
            avoided_segment_ids=[flooded.segment_id],
            reason="Every way to this point crosses water too deep for a car.",
        ),
    ]
    return requests, responses


def dump(name, models):
    data = [m.model_dump(mode="json") for m in models]
    (OUT / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def main():
    OUT.mkdir(exist_ok=True)
    segments = build_segments()
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "id": s.segment_id, "geometry": s.geometry.model_dump(mode="json"), "properties": s.model_dump(mode="json", exclude={"geometry"})}
            for s in segments
        ],
    }
    (OUT / "segments.geojson").write_text(json.dumps(geojson, indent=2, ensure_ascii=False) + "\n")
    dump("segments.json", segments)
    dump("risk.json", build_risk(segments))
    for name, models in build_scene(segments).items():
        dump(f"{name}.json", models)
    requests, responses = build_routes(segments)
    dump("route_requests.json", requests)
    dump("routes.json", responses)
    print(f"{len(segments)} segments written to {OUT.relative_to(ROOT.parent)}")


if __name__ == "__main__":
    main()
