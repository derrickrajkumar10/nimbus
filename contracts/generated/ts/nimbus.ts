/* Generated from contracts/schema/nimbus.schema.json. Do not edit; run contracts/generate.sh. */

/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "Agent".
 */
export type Agent =
  "sentinel" | "verifier" | "triage" | "pathfinder" | "dispatcher" | "herald" | "chronicler" | "commander";
export type EventId = string;
export type RunId = string;
export type SimTime = string;
/**
 * Wall time, for logs only. Domain logic uses sim_time.
 */
export type EmittedAt = string;
export type Source = string;
export type Type = "agent.activity";
export type Saw = string;
export type Decided = string;
export type Why = string;
export type AlertId = string;
export type RunId1 = string;
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "AlertScope".
 */
export type AlertScope = "place" | "ward";
export type SentAt = string;
export type SegmentIds = string[];
export type RecipientCount = number;
export type MessageEn = string;
export type MessageTa = string;
/**
 * Set for Ward Alerts, which go out only via an approved Proposal.
 */
export type ProposalId = string | null;
export type EventId1 = string;
export type RunId2 = string;
export type SimTime1 = string;
/**
 * Wall time, for logs only. Domain logic uses sim_time.
 */
export type EmittedAt1 = string;
export type Source1 = string;
export type Type1 = "alert.sent";
export type EventId2 = string;
export type RunId3 = string;
export type SimTime2 = string;
/**
 * Wall time, for logs only. Domain logic uses sim_time.
 */
export type EmittedAt2 = string;
export type Source2 = string;
export type Type2 = "clock.tick";
export type StepMinutes = number;
export type TickIndex = number;
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "DepthBand".
 */
export type DepthBand = "dry" | "ankle" | "knee" | "waist" | "above_waist";
export type Lat = number;
export type Lon = number;
export type HazardId = string;
export type RunId4 = string;
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "HazardClass".
 */
export type HazardClass = "open_manhole" | "live_wire" | "fallen_tree" | "stranded_vehicle";
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "HazardOwner".
 */
export type HazardOwner = "corporation" | "power_utility";
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "HazardStatus".
 */
export type HazardStatus = "open" | "acknowledged" | "cleared";
export type DetectedAt = string;
export type NoGoRadiusM = number;
export type SourceReportId = string | null;
export type EventId3 = string;
export type RunId5 = string;
export type SimTime3 = string;
/**
 * Wall time, for logs only. Domain logic uses sim_time.
 */
export type EmittedAt3 = string;
export type Source3 = string;
export type Type3 = "hazard.detected";
export type Type4 = string;
/**
 * @minItems 2
 */
export type Coordinates = [[number, number], [number, number], ...[number, number][]];
export type TwoWheeler = boolean;
export type Car = boolean;
export type Ambulance = boolean;
export type EventId4 = string;
export type RunId6 = string;
export type SimTime4 = string;
/**
 * Wall time, for logs only. Domain logic uses sim_time.
 */
export type EmittedAt4 = string;
export type Source4 = string;
export type Type5 = "policy.decided";
export type Action = string;
export type Resource = string;
export type Allowed = boolean;
export type Reason = string;
export type ProposalId1 = string;
export type RunId7 = string;
export type CreatedAt = string;
export type Rank = number;
export type Reason1 = string;
export type Action1 = WorkOrder | WardAlertDraft;
export type Kind = "work_order";
export type ResourceId = string;
export type SegmentId = string;
export type BuildingsAffected = number;
export type ReadingIds = string[];
export type SosIds = string[];
export type Kind1 = "ward_alert";
export type MessageEn1 = string;
export type MessageTa1 = string;
export type RecipientCount1 = number;
export type ProposalStatus = "pending" | "approved" | "edited" | "rejected";
export type DecidedBy = string | null;
export type DecidedAt = string | null;
export type EventId5 = string;
export type RunId8 = string;
export type SimTime5 = string;
/**
 * Wall time, for logs only. Domain logic uses sim_time.
 */
export type EmittedAt5 = string;
export type Source5 = string;
export type Type6 = "proposal.created";
export type EventId6 = string;
export type RunId9 = string;
export type SimTime6 = string;
/**
 * Wall time, for logs only. Domain logic uses sim_time.
 */
export type EmittedAt6 = string;
export type Source6 = string;
export type Type7 = "proposal.decided";
export type ProposalId2 = string;
export type Decision = "approved" | "edited" | "rejected";
export type DecidedBy1 = string;
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "ProposalStatus".
 */
export type ProposalStatus1 = "pending" | "approved" | "edited" | "rejected";
export type SosId = string;
export type Rank1 = number;
export type DangerScore = number;
/**
 * @maxItems 3
 */
export type Reasons = [] | [Reason2] | [Reason2, Reason2] | [Reason2, Reason2, Reason2];
export type Code = string;
export type Text = string;
export type MergedSosIds = string[];
export type ReadingId = string;
export type RunId10 = string;
export type SegmentId1 = string;
export type ObservedAt = string;
export type ReferenceObject = string | null;
export type Confidence = number;
/**
 * Reports merged into this Reading.
 *
 * @minItems 1
 */
export type ReportIds = [string, ...string[]];
export type HazardsSeen = HazardClass[];
export type ReportId = string;
export type RunId11 = string;
/**
 * Anonymous app-install identity.
 */
export type ReporterId = string;
export type CapturedAt = string;
/**
 * S3 object key of the photo.
 */
export type PhotoKey = string;
export type Note = string | null;
export type ReportSource = "app" | "simulated";
export type EventId7 = string;
export type RunId12 = string;
export type SimTime7 = string;
/**
 * Wall time, for logs only. Domain logic uses sim_time.
 */
export type EmittedAt7 = string;
export type Source7 = string;
export type Type8 = "report.created";
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "ReportSource".
 */
export type ReportSource1 = "app" | "simulated";
export type EventId8 = string;
export type RunId13 = string;
export type SimTime8 = string;
/**
 * Wall time, for logs only. Domain logic uses sim_time.
 */
export type EmittedAt8 = string;
export type Source8 = string;
export type Type9 = "report.verified";
export type ResourceId1 = string;
export type RunId14 = string;
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "ResourceKind".
 */
export type ResourceKind = "pump" | "desilting_crew" | "tree_crew";
export type Label = string;
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "ResourceStatus".
 */
export type ResourceStatus = "free" | "en_route" | "working";
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "RiskBand".
 */
export type RiskBand = "low" | "watch" | "likely" | "flooded";
export type EventId9 = string;
export type RunId15 = string;
export type SimTime9 = string;
/**
 * Wall time, for logs only. Domain logic uses sim_time.
 */
export type EmittedAt9 = string;
export type Source9 = string;
export type Type10 = "risk.changed";
export type SegmentId2 = string;
export type Score = number;
export type MinutesToFlood = number | null;
/**
 * @maxItems 3
 */
export type Reasons1 = [] | [Reason2] | [Reason2, Reason2] | [Reason2, Reason2, Reason2];
export type RunId16 = string;
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "VehicleType".
 */
export type VehicleType = "two_wheeler" | "car" | "ambulance";
export type RunId17 = string;
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "RouteStatus".
 */
export type RouteStatus = "ok" | "no_safe_route";
export type DistanceM = number | null;
export type DurationS = number | null;
/**
 * Segments the route keeps out of, flooded now or expected to flood before arrival.
 */
export type AvoidedSegmentIds = string[];
/**
 * One line for the traveller, in English.
 */
export type Reason3 = string;
export type PlaceId = string;
export type DeviceId = string;
export type Label1 = string;
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "SavedPlaceKind".
 */
export type SavedPlaceKind = "home" | "office" | "school" | "vehicle_parking" | "other";
export type RadiusM = number;
export type SegmentIds1 = string[];
export type SegmentId3 = string;
export type OsmWayId = number;
export type StreetName = string | null;
export type Ward = string;
export type LengthM = number;
/**
 * Accumulated rain over the rolling window at which this Segment floods, from terrain alone.
 */
export type BaselineThresholdMm = number;
export type DepressionDepthM = number;
export type CatchmentAreaM2 = number;
export type DistanceToWaterM = number;
/**
 * OSM building count in the catchment; the impact proxy.
 */
export type BuildingsNearby = number;
export type RunId18 = string;
export type SegmentId4 = string;
export type SimTime10 = string;
export type Score1 = number;
/**
 * None when flooding isn't expected within the forecast horizon.
 */
export type MinutesToFlood1 = number | null;
/**
 * @maxItems 3
 */
export type Reasons2 = [] | [Reason2] | [Reason2, Reason2] | [Reason2, Reason2, Reason2];
/**
 * Baseline Threshold after Reading nudges in this Run.
 */
export type FloodThresholdMm = number;
export type SosId1 = string;
export type RunId19 = string;
export type ReporterId1 = string;
export type CreatedAt1 = string;
export type PeopleCount = number;
export type Elderly = boolean;
export type Child = boolean;
export type Medical = boolean;
export type PhotoKey1 = string | null;
export type EventId10 = string;
export type RunId20 = string;
export type SimTime11 = string;
/**
 * Wall time, for logs only. Domain logic uses sim_time.
 */
export type EmittedAt10 = string;
export type Source10 = string;
export type Type11 = "sos.created";
export type EventId11 = string;
export type RunId21 = string;
export type SimTime12 = string;
/**
 * Wall time, for logs only. Domain logic uses sim_time.
 */
export type EmittedAt11 = string;
export type Source11 = string;
export type Type12 = "sos.ranked";
export type Ranking = RankedSos[];
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "Event".
 */
export type Event =
  | ClockTick
  | RiskChanged
  | ReportCreated
  | ReportVerified
  | HazardDetected
  | SosCreated
  | SosRanked
  | ProposalCreated
  | ProposalDecided
  | AlertSent
  | PolicyDecided
  | AgentActivity;

export interface Nimbus {
  [k: string]: unknown;
}
/**
 * One line in the console's agent activity feed.
 *
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "AgentActivity".
 */
export interface AgentActivity {
  event_id: EventId;
  run_id: RunId;
  sim_time: SimTime;
  emitted_at: EmittedAt;
  source: Source;
  type?: Type;
  detail: AgentActivityDetail;
}
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "AgentActivityDetail".
 */
export interface AgentActivityDetail {
  agent: Agent;
  saw: Saw;
  decided: Decided;
  why: Why;
}
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "Alert".
 */
export interface Alert {
  alert_id: AlertId;
  run_id: RunId1;
  scope: AlertScope;
  sent_at: SentAt;
  segment_ids: SegmentIds;
  recipient_count: RecipientCount;
  message_en: MessageEn;
  message_ta: MessageTa;
  proposal_id?: ProposalId;
}
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "AlertSent".
 */
export interface AlertSent {
  event_id: EventId1;
  run_id: RunId2;
  sim_time: SimTime1;
  emitted_at: EmittedAt1;
  source: Source1;
  type?: Type1;
  detail: Alert;
}
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "ClockTick".
 */
export interface ClockTick {
  event_id: EventId2;
  run_id: RunId3;
  sim_time: SimTime2;
  emitted_at: EmittedAt2;
  source: Source2;
  type?: Type2;
  step_minutes?: StepMinutes;
  tick_index: TickIndex;
}
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "GeoPoint".
 */
export interface GeoPoint {
  lat: Lat;
  lon: Lon;
}
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "Hazard".
 */
export interface Hazard {
  hazard_id: HazardId;
  run_id: RunId4;
  hazard_class: HazardClass;
  location: GeoPoint;
  owner: HazardOwner;
  status: HazardStatus;
  detected_at: DetectedAt;
  no_go_radius_m?: NoGoRadiusM;
  source_report_id?: SourceReportId;
}
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "HazardDetected".
 */
export interface HazardDetected {
  event_id: EventId3;
  run_id: RunId5;
  sim_time: SimTime3;
  emitted_at: EmittedAt3;
  source: Source3;
  type?: Type3;
  detail: Hazard;
}
/**
 * GeoJSON LineString geometry. Coordinates are [lon, lat].
 *
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "LineString".
 */
export interface LineString {
  type?: Type4;
  coordinates: Coordinates;
}
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "Passability".
 */
export interface Passability {
  two_wheeler: TwoWheeler;
  car: Car;
  ambulance: Ambulance;
}
/**
 * Every Cedar decision, allowed or denied. Feeds the console activity feed.
 *
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "PolicyDecided".
 */
export interface PolicyDecided {
  event_id: EventId4;
  run_id: RunId6;
  sim_time: SimTime4;
  emitted_at: EmittedAt4;
  source: Source4;
  type?: Type5;
  detail: PolicyDecidedDetail;
}
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "PolicyDecidedDetail".
 */
export interface PolicyDecidedDetail {
  principal: Agent;
  action: Action;
  resource: Resource;
  allowed: Allowed;
  reason: Reason;
}
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "Proposal".
 */
export interface Proposal {
  proposal_id: ProposalId1;
  run_id: RunId7;
  proposed_by: Agent;
  created_at: CreatedAt;
  rank: Rank;
  reason: Reason1;
  action: Action1;
  status?: ProposalStatus;
  decided_by?: DecidedBy;
  decided_at?: DecidedAt;
}
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "WorkOrder".
 */
export interface WorkOrder {
  kind?: Kind;
  resource_id: ResourceId;
  segment_id: SegmentId;
  buildings_affected: BuildingsAffected;
  reading_ids?: ReadingIds;
  sos_ids?: SosIds;
}
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "WardAlertDraft".
 */
export interface WardAlertDraft {
  kind?: Kind1;
  message_en: MessageEn1;
  message_ta: MessageTa1;
  recipient_count: RecipientCount1;
}
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "ProposalCreated".
 */
export interface ProposalCreated {
  event_id: EventId5;
  run_id: RunId8;
  sim_time: SimTime5;
  emitted_at: EmittedAt5;
  source: Source5;
  type?: Type6;
  detail: Proposal;
}
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "ProposalDecided".
 */
export interface ProposalDecided {
  event_id: EventId6;
  run_id: RunId9;
  sim_time: SimTime6;
  emitted_at: EmittedAt6;
  source: Source6;
  type?: Type7;
  detail: ProposalDecidedDetail;
}
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "ProposalDecidedDetail".
 */
export interface ProposalDecidedDetail {
  proposal_id: ProposalId2;
  decision: Decision;
  decided_by: DecidedBy1;
  proposal: Proposal1;
}
/**
 * The Proposal as approved, including any officer edits.
 */
export interface Proposal1 {
  proposal_id: ProposalId1;
  run_id: RunId7;
  proposed_by: Agent;
  created_at: CreatedAt;
  rank: Rank;
  reason: Reason1;
  action: Action1;
  status?: ProposalStatus;
  decided_by?: DecidedBy;
  decided_at?: DecidedAt;
}
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "RankedSos".
 */
export interface RankedSos {
  sos_id: SosId;
  rank: Rank1;
  danger_score: DangerScore;
  reasons: Reasons;
  merged_sos_ids?: MergedSosIds;
}
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "Reason".
 */
export interface Reason2 {
  code: Code;
  text: Text;
}
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "Reading".
 */
export interface Reading {
  reading_id: ReadingId;
  run_id: RunId10;
  segment_id: SegmentId1;
  observed_at: ObservedAt;
  depth: DepthBand;
  reference_object: ReferenceObject;
  confidence: Confidence;
  passable: Passability;
  report_ids: ReportIds;
  hazards_seen?: HazardsSeen;
}
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "Report".
 */
export interface Report {
  report_id: ReportId;
  run_id: RunId11;
  reporter_id: ReporterId;
  captured_at: CapturedAt;
  location: GeoPoint;
  photo_key: PhotoKey;
  note?: Note;
  source?: ReportSource;
}
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "ReportCreated".
 */
export interface ReportCreated {
  event_id: EventId7;
  run_id: RunId12;
  sim_time: SimTime7;
  emitted_at: EmittedAt7;
  source: Source7;
  type?: Type8;
  detail: Report;
}
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "ReportVerified".
 */
export interface ReportVerified {
  event_id: EventId8;
  run_id: RunId13;
  sim_time: SimTime8;
  emitted_at: EmittedAt8;
  source: Source8;
  type?: Type9;
  detail: Reading;
}
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "Resource".
 */
export interface Resource1 {
  resource_id: ResourceId1;
  run_id: RunId14;
  kind: ResourceKind;
  label: Label;
  status: ResourceStatus;
  location: GeoPoint;
}
/**
 * Fires only when a Segment crosses a Risk Band.
 *
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "RiskChanged".
 */
export interface RiskChanged {
  event_id: EventId9;
  run_id: RunId15;
  sim_time: SimTime9;
  emitted_at: EmittedAt9;
  source: Source9;
  type?: Type10;
  detail: RiskChangedDetail;
}
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "RiskChangedDetail".
 */
export interface RiskChangedDetail {
  segment_id: SegmentId2;
  previous_band: RiskBand;
  band: RiskBand;
  score: Score;
  minutes_to_flood: MinutesToFlood;
  reasons: Reasons1;
}
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "RouteRequest".
 */
export interface RouteRequest {
  run_id: RunId16;
  origin: GeoPoint;
  destination: GeoPoint;
  vehicle: VehicleType;
}
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "RouteResponse".
 */
export interface RouteResponse {
  run_id: RunId17;
  status: RouteStatus;
  /**
   * The route. None when status is no_safe_route.
   */
  geometry?: LineString | null;
  distance_m?: DistanceM;
  duration_s?: DurationS;
  avoided_segment_ids?: AvoidedSegmentIds;
  reason: Reason3;
}
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "SavedPlace".
 */
export interface SavedPlace {
  place_id: PlaceId;
  device_id: DeviceId;
  label: Label1;
  kind: SavedPlaceKind;
  location: GeoPoint;
  radius_m?: RadiusM;
  segment_ids: SegmentIds1;
}
/**
 * Static, run-independent. Produced once by F1 and frozen.
 *
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "Segment".
 */
export interface Segment {
  segment_id: SegmentId3;
  osm_way_id: OsmWayId;
  street_name: StreetName;
  ward: Ward;
  geometry: LineString;
  length_m: LengthM;
  baseline_threshold_mm: BaselineThresholdMm;
  terrain: TerrainFactors;
  buildings_nearby: BuildingsNearby;
}
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "TerrainFactors".
 */
export interface TerrainFactors {
  depression_depth_m: DepressionDepthM;
  catchment_area_m2: CatchmentAreaM2;
  distance_to_water_m: DistanceToWaterM;
}
/**
 * A Segment's current state within one Run.
 *
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "SegmentRisk".
 */
export interface SegmentRisk {
  run_id: RunId18;
  segment_id: SegmentId4;
  sim_time: SimTime10;
  score: Score1;
  band: RiskBand;
  minutes_to_flood: MinutesToFlood1;
  reasons: Reasons2;
  flood_threshold_mm: FloodThresholdMm;
}
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "Sos".
 */
export interface Sos {
  sos_id: SosId1;
  run_id: RunId19;
  reporter_id: ReporterId1;
  created_at: CreatedAt1;
  location: GeoPoint;
  people_count: PeopleCount;
  flags: VulnerabilityFlags;
  photo_key?: PhotoKey1;
}
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "VulnerabilityFlags".
 */
export interface VulnerabilityFlags {
  elderly?: Elderly;
  child?: Child;
  medical?: Medical;
}
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "SosCreated".
 */
export interface SosCreated {
  event_id: EventId10;
  run_id: RunId20;
  sim_time: SimTime11;
  emitted_at: EmittedAt10;
  source: Source10;
  type?: Type11;
  detail: Sos;
}
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "SosRanked".
 */
export interface SosRanked {
  event_id: EventId11;
  run_id: RunId21;
  sim_time: SimTime12;
  emitted_at: EmittedAt11;
  source: Source11;
  type?: Type12;
  detail: SosRankedDetail;
}
/**
 * This interface was referenced by `Nimbus`'s JSON-Schema
 * via the `definition` "SosRankedDetail".
 */
export interface SosRankedDetail {
  ranking: Ranking;
}
