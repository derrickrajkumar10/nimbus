"""Shared value types. Names follow CONTEXT.md."""

from enum import StrEnum
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

# "live" or "replay-<slug>". See docs/adr/0001-runs-isolate-replay-state.md.
RunId = Annotated[str, Field(pattern=r"^(live|replay-[a-z0-9-]+)$", examples=["live", "replay-michaung"])]

# "{osm_way_id}-{n}", n counting sub-segments along the way from 0. See segments.py.
SegmentId = Annotated[str, Field(pattern=r"^\d+-\d+$", examples=["27320162-0"])]

# Storm time, not wall time. Domain code never reads the wall clock.
SimTime = AwareDatetime

Score = Annotated[int, Field(ge=0, le=100)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=True)


class RiskBand(StrEnum):
    LOW = "low"
    WATCH = "watch"
    LIKELY = "likely"
    FLOODED = "flooded"  # only ever set by a Reading, never by the Risk Score


class DepthBand(StrEnum):
    DRY = "dry"
    ANKLE = "ankle"
    KNEE = "knee"
    WAIST = "waist"
    ABOVE_WAIST = "above_waist"


DEPTH_ORDER = [DepthBand.DRY, DepthBand.ANKLE, DepthBand.KNEE, DepthBand.WAIST, DepthBand.ABOVE_WAIST]


class VehicleType(StrEnum):
    TWO_WHEELER = "two_wheeler"
    CAR = "car"
    AMBULANCE = "ambulance"


class HazardClass(StrEnum):
    OPEN_MANHOLE = "open_manhole"
    LIVE_WIRE = "live_wire"
    FALLEN_TREE = "fallen_tree"
    STRANDED_VEHICLE = "stranded_vehicle"


class HazardOwner(StrEnum):
    CORPORATION = "corporation"  # Greater Chennai Corporation
    POWER_UTILITY = "power_utility"


class ResourceKind(StrEnum):
    PUMP = "pump"
    DESILTING_CREW = "desilting_crew"
    TREE_CREW = "tree_crew"


class Agent(StrEnum):
    SENTINEL = "sentinel"
    VERIFIER = "verifier"
    TRIAGE = "triage"
    PATHFINDER = "pathfinder"
    DISPATCHER = "dispatcher"
    HERALD = "herald"
    CHRONICLER = "chronicler"
    COMMANDER = "commander"


class GeoPoint(Contract):
    lat: Annotated[float, Field(ge=-90, le=90)]
    lon: Annotated[float, Field(ge=-180, le=180)]


class LineString(Contract):
    """GeoJSON LineString geometry. Coordinates are [lon, lat]."""

    type: Annotated[str, Field(pattern="^LineString$")] = "LineString"
    coordinates: Annotated[list[Annotated[list[float], Field(min_length=2, max_length=2)]], Field(min_length=2)]


class Reason(Contract):
    code: Annotated[str, Field(examples=["forecast_exceeds_threshold", "antecedent_rain", "high_tide", "nearby_reading"])]
    text: Annotated[str, Field(examples=["38 mm forecast in 3 h against a 30 mm threshold"])]
