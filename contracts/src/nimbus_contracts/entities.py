"""Domain entities. Every mutable entity carries a run_id (ADR 0001)."""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field

from .common import (
    Agent,
    Contract,
    DepthBand,
    GeoPoint,
    HazardClass,
    HazardOwner,
    LineString,
    Reason,
    ResourceKind,
    RiskBand,
    RunId,
    Score,
    SegmentId,
    SimTime,
    VehicleType,
)

# --- Place ---------------------------------------------------------------


class TerrainFactors(Contract):
    depression_depth_m: Annotated[float, Field(ge=0)]
    catchment_area_m2: Annotated[float, Field(ge=0)]
    distance_to_water_m: Annotated[float, Field(ge=0)]


class Segment(Contract):
    """Static, run-independent. Produced once by F1 and frozen."""

    segment_id: SegmentId
    osm_way_id: int
    street_name: str | None
    ward: Annotated[str, Field(examples=["velachery"])]
    geometry: LineString
    length_m: Annotated[float, Field(gt=0)]
    baseline_threshold_mm: Annotated[float, Field(gt=0, description="Accumulated rain over the rolling window at which this Segment floods, from terrain alone.")]
    terrain: TerrainFactors
    buildings_nearby: Annotated[int, Field(ge=0, description="OSM building count in the catchment; the impact proxy.")]


class SegmentRisk(Contract):
    """A Segment's current state within one Run."""

    run_id: RunId
    segment_id: SegmentId
    sim_time: SimTime
    score: Score
    band: RiskBand
    minutes_to_flood: Annotated[int | None, Field(ge=0, description="None when flooding isn't expected within the forecast horizon.")]
    reasons: Annotated[list[Reason], Field(max_length=3)]
    flood_threshold_mm: Annotated[float, Field(gt=0, description="Baseline Threshold after Reading nudges in this Run.")]


# --- Observation ---------------------------------------------------------


class ReportSource(StrEnum):
    APP = "app"
    SIMULATED = "simulated"  # team-authored Replay Reports, shown as simulated on screen


class Report(Contract):
    report_id: str
    run_id: RunId
    reporter_id: Annotated[str, Field(description="Anonymous app-install identity.")]
    captured_at: SimTime
    location: GeoPoint
    photo_key: Annotated[str, Field(description="S3 object key of the photo.")]
    note: str | None = None
    source: ReportSource = ReportSource.APP


class Passability(Contract):
    two_wheeler: bool
    car: bool
    ambulance: bool


class Reading(Contract):
    reading_id: str
    run_id: RunId
    segment_id: SegmentId
    observed_at: SimTime
    depth: DepthBand
    reference_object: Annotated[str | None, Field(examples=["kerb", "tyre", "knee", "wall"])]
    confidence: Annotated[float, Field(ge=0, le=1)]
    passable: Passability
    report_ids: Annotated[list[str], Field(min_length=1, description="Reports merged into this Reading.")]
    hazards_seen: list[HazardClass] = []


class HazardStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    CLEARED = "cleared"


class Hazard(Contract):
    hazard_id: str
    run_id: RunId
    hazard_class: HazardClass
    location: GeoPoint
    owner: HazardOwner
    status: HazardStatus
    detected_at: SimTime
    no_go_radius_m: Annotated[float, Field(gt=0)] = 30
    source_report_id: str | None = None


class VulnerabilityFlags(Contract):
    elderly: bool = False
    child: bool = False
    medical: bool = False


class Sos(Contract):
    sos_id: str
    run_id: RunId
    reporter_id: str
    created_at: SimTime
    location: GeoPoint
    people_count: Annotated[int, Field(ge=1)]
    flags: VulnerabilityFlags
    photo_key: str | None = None


class RankedSos(Contract):
    sos_id: str
    rank: Annotated[int, Field(ge=1)]
    danger_score: Score
    reasons: Annotated[list[Reason], Field(max_length=3)]
    merged_sos_ids: list[str] = []


# --- Response ------------------------------------------------------------


class SavedPlaceKind(StrEnum):
    HOME = "home"
    OFFICE = "office"
    SCHOOL = "school"
    VEHICLE_PARKING = "vehicle_parking"
    OTHER = "other"


class SavedPlace(Contract):
    place_id: str
    device_id: str
    label: str
    kind: SavedPlaceKind
    location: GeoPoint
    radius_m: Annotated[float, Field(gt=0)] = 150
    segment_ids: list[SegmentId]


class ResourceStatus(StrEnum):
    FREE = "free"
    EN_ROUTE = "en_route"
    WORKING = "working"


class Resource(Contract):
    resource_id: str
    run_id: RunId
    kind: ResourceKind
    label: Annotated[str, Field(examples=["Pump 2"])]
    status: ResourceStatus
    location: GeoPoint


class WorkOrder(Contract):
    kind: Literal["work_order"] = "work_order"
    resource_id: str
    segment_id: SegmentId
    buildings_affected: Annotated[int, Field(ge=0)]
    reading_ids: list[str] = []
    sos_ids: list[str] = []


class WardAlertDraft(Contract):
    kind: Literal["ward_alert"] = "ward_alert"
    message_en: str
    message_ta: str
    recipient_count: Annotated[int, Field(ge=0)]


class ProposalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    EDITED = "edited"  # approved with officer changes
    REJECTED = "rejected"


class Proposal(Contract):
    proposal_id: str
    run_id: RunId
    proposed_by: Agent
    created_at: SimTime
    rank: Annotated[int, Field(ge=1)]
    reason: str
    action: Annotated[WorkOrder | WardAlertDraft, Field(discriminator="kind")]
    status: ProposalStatus = ProposalStatus.PENDING
    decided_by: str | None = None
    decided_at: SimTime | None = None


class AlertScope(StrEnum):
    PLACE = "place"  # Subscribers with a Saved Place on affected Segments; no approval needed
    WARD = "ward"  # everyone in the Ward, or more than WARD_ALERT_RECIPIENT_THRESHOLD; needs approval


WARD_ALERT_RECIPIENT_THRESHOLD = 100


class Alert(Contract):
    alert_id: str
    run_id: RunId
    scope: AlertScope
    sent_at: SimTime
    segment_ids: list[SegmentId]
    recipient_count: Annotated[int, Field(ge=0)]
    message_en: str
    message_ta: str
    proposal_id: Annotated[str | None, Field(description="Set for Ward Alerts, which go out only via an approved Proposal.")] = None
