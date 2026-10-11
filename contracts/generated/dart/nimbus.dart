// To parse this JSON data, do
//
//     final segment = segmentFromJson(jsonString);
//     final segmentRisk = segmentRiskFromJson(jsonString);
//     final report = reportFromJson(jsonString);
//     final reading = readingFromJson(jsonString);
//     final hazard = hazardFromJson(jsonString);
//     final sos = sosFromJson(jsonString);
//     final rankedSos = rankedSosFromJson(jsonString);
//     final savedPlace = savedPlaceFromJson(jsonString);
//     final resource = resourceFromJson(jsonString);
//     final proposal = proposalFromJson(jsonString);
//     final alert = alertFromJson(jsonString);
//     final routeRequest = routeRequestFromJson(jsonString);
//     final routeResponse = routeResponseFromJson(jsonString);

import 'package:meta/meta.dart';
import 'dart:convert';

Segment segmentFromJson(String str) => Segment.fromJson(json.decode(str));

String segmentToJson(Segment data) => json.encode(data.toJson());

SegmentRisk segmentRiskFromJson(String str) => SegmentRisk.fromJson(json.decode(str));

String segmentRiskToJson(SegmentRisk data) => json.encode(data.toJson());

Report reportFromJson(String str) => Report.fromJson(json.decode(str));

String reportToJson(Report data) => json.encode(data.toJson());

Reading readingFromJson(String str) => Reading.fromJson(json.decode(str));

String readingToJson(Reading data) => json.encode(data.toJson());

Hazard hazardFromJson(String str) => Hazard.fromJson(json.decode(str));

String hazardToJson(Hazard data) => json.encode(data.toJson());

Sos sosFromJson(String str) => Sos.fromJson(json.decode(str));

String sosToJson(Sos data) => json.encode(data.toJson());

RankedSos rankedSosFromJson(String str) => RankedSos.fromJson(json.decode(str));

String rankedSosToJson(RankedSos data) => json.encode(data.toJson());

SavedPlace savedPlaceFromJson(String str) => SavedPlace.fromJson(json.decode(str));

String savedPlaceToJson(SavedPlace data) => json.encode(data.toJson());

Resource resourceFromJson(String str) => Resource.fromJson(json.decode(str));

String resourceToJson(Resource data) => json.encode(data.toJson());

Proposal proposalFromJson(String str) => Proposal.fromJson(json.decode(str));

String proposalToJson(Proposal data) => json.encode(data.toJson());

Alert alertFromJson(String str) => Alert.fromJson(json.decode(str));

String alertToJson(Alert data) => json.encode(data.toJson());

RouteRequest routeRequestFromJson(String str) => RouteRequest.fromJson(json.decode(str));

String routeRequestToJson(RouteRequest data) => json.encode(data.toJson());

RouteResponse routeResponseFromJson(String str) => RouteResponse.fromJson(json.decode(str));

String routeResponseToJson(RouteResponse data) => json.encode(data.toJson());


///Static, run-independent. Produced once by F1 and frozen.
class Segment {
    
    ///Accumulated rain over the rolling window at which this Segment floods, from terrain alone.
    double baselineThresholdMm;
    
    ///OSM building count in the catchment; the impact proxy.
    int buildingsNearby;
    LineString geometry;
    double lengthM;
    int osmWayId;
    String segmentId;
    String streetName;
    TerrainFactors terrain;
    String ward;

    Segment({
        required this.baselineThresholdMm,
        required this.buildingsNearby,
        required this.geometry,
        required this.lengthM,
        required this.osmWayId,
        required this.segmentId,
        required this.streetName,
        required this.terrain,
        required this.ward,
    });

    factory Segment.fromJson(Map<String, dynamic> json) => Segment(
        baselineThresholdMm: json["baseline_threshold_mm"]?.toDouble(),
        buildingsNearby: json["buildings_nearby"],
        geometry: LineString.fromJson(json["geometry"]),
        lengthM: json["length_m"]?.toDouble(),
        osmWayId: json["osm_way_id"],
        segmentId: json["segment_id"],
        streetName: json["street_name"],
        terrain: TerrainFactors.fromJson(json["terrain"]),
        ward: json["ward"],
    );

    Map<String, dynamic> toJson() => {
        "baseline_threshold_mm": baselineThresholdMm,
        "buildings_nearby": buildingsNearby,
        "geometry": geometry.toJson(),
        "length_m": lengthM,
        "osm_way_id": osmWayId,
        "segment_id": segmentId,
        "street_name": streetName,
        "terrain": terrain.toJson(),
        "ward": ward,
    };
}


///GeoJSON LineString geometry. Coordinates are [lon, lat].
class LineString {
    List<List<double>> coordinates;
    String type;

    LineString({
        required this.coordinates,
        required this.type,
    });

    factory LineString.fromJson(Map<String, dynamic> json) => LineString(
        coordinates: List<List<double>>.from(json["coordinates"].map((x) => List<double>.from(x.map((x) => x?.toDouble())))),
        type: json["type"],
    );

    Map<String, dynamic> toJson() => {
        "coordinates": List<dynamic>.from(coordinates.map((x) => List<dynamic>.from(x.map((x) => x)))),
        "type": type,
    };
}

class TerrainFactors {
    double catchmentAreaM2;
    double depressionDepthM;
    double distanceToWaterM;

    TerrainFactors({
        required this.catchmentAreaM2,
        required this.depressionDepthM,
        required this.distanceToWaterM,
    });

    factory TerrainFactors.fromJson(Map<String, dynamic> json) => TerrainFactors(
        catchmentAreaM2: json["catchment_area_m2"]?.toDouble(),
        depressionDepthM: json["depression_depth_m"]?.toDouble(),
        distanceToWaterM: json["distance_to_water_m"]?.toDouble(),
    );

    Map<String, dynamic> toJson() => {
        "catchment_area_m2": catchmentAreaM2,
        "depression_depth_m": depressionDepthM,
        "distance_to_water_m": distanceToWaterM,
    };
}


///A Segment's current state within one Run.
class SegmentRisk {
    RiskBand band;
    
    ///Baseline Threshold after Reading nudges in this Run.
    double floodThresholdMm;
    
    ///None when flooding isn't expected within the forecast horizon.
    int minutesToFlood;
    List<Reason> reasons;
    String runId;
    int score;
    String segmentId;
    DateTime simTime;

    SegmentRisk({
        required this.band,
        required this.floodThresholdMm,
        required this.minutesToFlood,
        required this.reasons,
        required this.runId,
        required this.score,
        required this.segmentId,
        required this.simTime,
    });

    factory SegmentRisk.fromJson(Map<String, dynamic> json) => SegmentRisk(
        band: riskBandValues.map[json["band"]]!,
        floodThresholdMm: json["flood_threshold_mm"]?.toDouble(),
        minutesToFlood: json["minutes_to_flood"],
        reasons: List<Reason>.from(json["reasons"].map((x) => Reason.fromJson(x))),
        runId: json["run_id"],
        score: json["score"],
        segmentId: json["segment_id"],
        simTime: DateTime.parse(json["sim_time"]),
    );

    Map<String, dynamic> toJson() => {
        "band": riskBandValues.reverse[band],
        "flood_threshold_mm": floodThresholdMm,
        "minutes_to_flood": minutesToFlood,
        "reasons": List<dynamic>.from(reasons.map((x) => x.toJson())),
        "run_id": runId,
        "score": score,
        "segment_id": segmentId,
        "sim_time": simTime.toIso8601String(),
    };
}

enum RiskBand {
    FLOODED,
    LIKELY,
    LOW,
    WATCH
}

final riskBandValues = EnumValues({
    "flooded": RiskBand.FLOODED,
    "likely": RiskBand.LIKELY,
    "low": RiskBand.LOW,
    "watch": RiskBand.WATCH
});

class Reason {
    String code;
    String text;

    Reason({
        required this.code,
        required this.text,
    });

    factory Reason.fromJson(Map<String, dynamic> json) => Reason(
        code: json["code"],
        text: json["text"],
    );

    Map<String, dynamic> toJson() => {
        "code": code,
        "text": text,
    };
}

class Report {
    DateTime capturedAt;
    GeoPoint location;
    String note;
    
    ///S3 object key of the photo.
    String photoKey;
    String reportId;
    
    ///Anonymous app-install identity.
    String reporterId;
    String runId;
    ReportSource source;

    Report({
        required this.capturedAt,
        required this.location,
        required this.note,
        required this.photoKey,
        required this.reportId,
        required this.reporterId,
        required this.runId,
        required this.source,
    });

    factory Report.fromJson(Map<String, dynamic> json) => Report(
        capturedAt: DateTime.parse(json["captured_at"]),
        location: GeoPoint.fromJson(json["location"]),
        note: json["note"],
        photoKey: json["photo_key"],
        reportId: json["report_id"],
        reporterId: json["reporter_id"],
        runId: json["run_id"],
        source: reportSourceValues.map[json["source"]]!,
    );

    Map<String, dynamic> toJson() => {
        "captured_at": capturedAt.toIso8601String(),
        "location": location.toJson(),
        "note": note,
        "photo_key": photoKey,
        "report_id": reportId,
        "reporter_id": reporterId,
        "run_id": runId,
        "source": reportSourceValues.reverse[source],
    };
}

class GeoPoint {
    double lat;
    double lon;

    GeoPoint({
        required this.lat,
        required this.lon,
    });

    factory GeoPoint.fromJson(Map<String, dynamic> json) => GeoPoint(
        lat: json["lat"]?.toDouble(),
        lon: json["lon"]?.toDouble(),
    );

    Map<String, dynamic> toJson() => {
        "lat": lat,
        "lon": lon,
    };
}

enum ReportSource {
    APP,
    SIMULATED
}

final reportSourceValues = EnumValues({
    "app": ReportSource.APP,
    "simulated": ReportSource.SIMULATED
});

class Reading {
    double confidence;
    DepthBand depth;
    List<HazardClass> hazardsSeen;
    DateTime observedAt;
    Passability passable;
    String readingId;
    String referenceObject;
    
    ///Reports merged into this Reading.
    List<String> reportIds;
    String runId;
    String segmentId;

    Reading({
        required this.confidence,
        required this.depth,
        required this.hazardsSeen,
        required this.observedAt,
        required this.passable,
        required this.readingId,
        required this.referenceObject,
        required this.reportIds,
        required this.runId,
        required this.segmentId,
    });

    factory Reading.fromJson(Map<String, dynamic> json) => Reading(
        confidence: json["confidence"]?.toDouble(),
        depth: depthBandValues.map[json["depth"]]!,
        hazardsSeen: List<HazardClass>.from(json["hazards_seen"].map((x) => hazardClassValues.map[x]!)),
        observedAt: DateTime.parse(json["observed_at"]),
        passable: Passability.fromJson(json["passable"]),
        readingId: json["reading_id"],
        referenceObject: json["reference_object"],
        reportIds: List<String>.from(json["report_ids"].map((x) => x)),
        runId: json["run_id"],
        segmentId: json["segment_id"],
    );

    Map<String, dynamic> toJson() => {
        "confidence": confidence,
        "depth": depthBandValues.reverse[depth],
        "hazards_seen": List<dynamic>.from(hazardsSeen.map((x) => hazardClassValues.reverse[x])),
        "observed_at": observedAt.toIso8601String(),
        "passable": passable.toJson(),
        "reading_id": readingId,
        "reference_object": referenceObject,
        "report_ids": List<dynamic>.from(reportIds.map((x) => x)),
        "run_id": runId,
        "segment_id": segmentId,
    };
}

enum DepthBand {
    ABOVE_WAIST,
    ANKLE,
    DRY,
    KNEE,
    WAIST
}

final depthBandValues = EnumValues({
    "above_waist": DepthBand.ABOVE_WAIST,
    "ankle": DepthBand.ANKLE,
    "dry": DepthBand.DRY,
    "knee": DepthBand.KNEE,
    "waist": DepthBand.WAIST
});

enum HazardClass {
    FALLEN_TREE,
    LIVE_WIRE,
    OPEN_MANHOLE,
    STRANDED_VEHICLE
}

final hazardClassValues = EnumValues({
    "fallen_tree": HazardClass.FALLEN_TREE,
    "live_wire": HazardClass.LIVE_WIRE,
    "open_manhole": HazardClass.OPEN_MANHOLE,
    "stranded_vehicle": HazardClass.STRANDED_VEHICLE
});

class Passability {
    bool ambulance;
    bool car;
    bool twoWheeler;

    Passability({
        required this.ambulance,
        required this.car,
        required this.twoWheeler,
    });

    factory Passability.fromJson(Map<String, dynamic> json) => Passability(
        ambulance: json["ambulance"],
        car: json["car"],
        twoWheeler: json["two_wheeler"],
    );

    Map<String, dynamic> toJson() => {
        "ambulance": ambulance,
        "car": car,
        "two_wheeler": twoWheeler,
    };
}

class Hazard {
    DateTime detectedAt;
    HazardClass hazardClass;
    String hazardId;
    GeoPoint location;
    double noGoRadiusM;
    HazardOwner owner;
    String runId;
    String sourceReportId;
    HazardStatus status;

    Hazard({
        required this.detectedAt,
        required this.hazardClass,
        required this.hazardId,
        required this.location,
        required this.noGoRadiusM,
        required this.owner,
        required this.runId,
        required this.sourceReportId,
        required this.status,
    });

    factory Hazard.fromJson(Map<String, dynamic> json) => Hazard(
        detectedAt: DateTime.parse(json["detected_at"]),
        hazardClass: hazardClassValues.map[json["hazard_class"]]!,
        hazardId: json["hazard_id"],
        location: GeoPoint.fromJson(json["location"]),
        noGoRadiusM: json["no_go_radius_m"]?.toDouble(),
        owner: hazardOwnerValues.map[json["owner"]]!,
        runId: json["run_id"],
        sourceReportId: json["source_report_id"],
        status: hazardStatusValues.map[json["status"]]!,
    );

    Map<String, dynamic> toJson() => {
        "detected_at": detectedAt.toIso8601String(),
        "hazard_class": hazardClassValues.reverse[hazardClass],
        "hazard_id": hazardId,
        "location": location.toJson(),
        "no_go_radius_m": noGoRadiusM,
        "owner": hazardOwnerValues.reverse[owner],
        "run_id": runId,
        "source_report_id": sourceReportId,
        "status": hazardStatusValues.reverse[status],
    };
}

enum HazardOwner {
    CORPORATION,
    POWER_UTILITY
}

final hazardOwnerValues = EnumValues({
    "corporation": HazardOwner.CORPORATION,
    "power_utility": HazardOwner.POWER_UTILITY
});

enum HazardStatus {
    ACKNOWLEDGED,
    CLEARED,
    OPEN
}

final hazardStatusValues = EnumValues({
    "acknowledged": HazardStatus.ACKNOWLEDGED,
    "cleared": HazardStatus.CLEARED,
    "open": HazardStatus.OPEN
});

class Sos {
    DateTime createdAt;
    VulnerabilityFlags flags;
    GeoPoint location;
    int peopleCount;
    String photoKey;
    String reporterId;
    String runId;
    String sosId;

    Sos({
        required this.createdAt,
        required this.flags,
        required this.location,
        required this.peopleCount,
        required this.photoKey,
        required this.reporterId,
        required this.runId,
        required this.sosId,
    });

    factory Sos.fromJson(Map<String, dynamic> json) => Sos(
        createdAt: DateTime.parse(json["created_at"]),
        flags: VulnerabilityFlags.fromJson(json["flags"]),
        location: GeoPoint.fromJson(json["location"]),
        peopleCount: json["people_count"],
        photoKey: json["photo_key"],
        reporterId: json["reporter_id"],
        runId: json["run_id"],
        sosId: json["sos_id"],
    );

    Map<String, dynamic> toJson() => {
        "created_at": createdAt.toIso8601String(),
        "flags": flags.toJson(),
        "location": location.toJson(),
        "people_count": peopleCount,
        "photo_key": photoKey,
        "reporter_id": reporterId,
        "run_id": runId,
        "sos_id": sosId,
    };
}

class VulnerabilityFlags {
    bool child;
    bool elderly;
    bool medical;

    VulnerabilityFlags({
        required this.child,
        required this.elderly,
        required this.medical,
    });

    factory VulnerabilityFlags.fromJson(Map<String, dynamic> json) => VulnerabilityFlags(
        child: json["child"],
        elderly: json["elderly"],
        medical: json["medical"],
    );

    Map<String, dynamic> toJson() => {
        "child": child,
        "elderly": elderly,
        "medical": medical,
    };
}

class RankedSos {
    int dangerScore;
    List<String> mergedSosIds;
    int rank;
    List<Reason> reasons;
    String sosId;

    RankedSos({
        required this.dangerScore,
        required this.mergedSosIds,
        required this.rank,
        required this.reasons,
        required this.sosId,
    });

    factory RankedSos.fromJson(Map<String, dynamic> json) => RankedSos(
        dangerScore: json["danger_score"],
        mergedSosIds: List<String>.from(json["merged_sos_ids"].map((x) => x)),
        rank: json["rank"],
        reasons: List<Reason>.from(json["reasons"].map((x) => Reason.fromJson(x))),
        sosId: json["sos_id"],
    );

    Map<String, dynamic> toJson() => {
        "danger_score": dangerScore,
        "merged_sos_ids": List<dynamic>.from(mergedSosIds.map((x) => x)),
        "rank": rank,
        "reasons": List<dynamic>.from(reasons.map((x) => x.toJson())),
        "sos_id": sosId,
    };
}

class SavedPlace {
    String deviceId;
    SavedPlaceKind kind;
    String label;
    GeoPoint location;
    String placeId;
    double radiusM;
    List<String> segmentIds;

    SavedPlace({
        required this.deviceId,
        required this.kind,
        required this.label,
        required this.location,
        required this.placeId,
        required this.radiusM,
        required this.segmentIds,
    });

    factory SavedPlace.fromJson(Map<String, dynamic> json) => SavedPlace(
        deviceId: json["device_id"],
        kind: savedPlaceKindValues.map[json["kind"]]!,
        label: json["label"],
        location: GeoPoint.fromJson(json["location"]),
        placeId: json["place_id"],
        radiusM: json["radius_m"]?.toDouble(),
        segmentIds: List<String>.from(json["segment_ids"].map((x) => x)),
    );

    Map<String, dynamic> toJson() => {
        "device_id": deviceId,
        "kind": savedPlaceKindValues.reverse[kind],
        "label": label,
        "location": location.toJson(),
        "place_id": placeId,
        "radius_m": radiusM,
        "segment_ids": List<dynamic>.from(segmentIds.map((x) => x)),
    };
}

enum SavedPlaceKind {
    HOME,
    OFFICE,
    OTHER,
    SCHOOL,
    VEHICLE_PARKING
}

final savedPlaceKindValues = EnumValues({
    "home": SavedPlaceKind.HOME,
    "office": SavedPlaceKind.OFFICE,
    "other": SavedPlaceKind.OTHER,
    "school": SavedPlaceKind.SCHOOL,
    "vehicle_parking": SavedPlaceKind.VEHICLE_PARKING
});

class Resource {
    ResourceKind kind;
    String label;
    GeoPoint location;
    String resourceId;
    String runId;
    ResourceStatus status;

    Resource({
        required this.kind,
        required this.label,
        required this.location,
        required this.resourceId,
        required this.runId,
        required this.status,
    });

    factory Resource.fromJson(Map<String, dynamic> json) => Resource(
        kind: resourceKindValues.map[json["kind"]]!,
        label: json["label"],
        location: GeoPoint.fromJson(json["location"]),
        resourceId: json["resource_id"],
        runId: json["run_id"],
        status: resourceStatusValues.map[json["status"]]!,
    );

    Map<String, dynamic> toJson() => {
        "kind": resourceKindValues.reverse[kind],
        "label": label,
        "location": location.toJson(),
        "resource_id": resourceId,
        "run_id": runId,
        "status": resourceStatusValues.reverse[status],
    };
}

enum ResourceKind {
    DESILTING_CREW,
    PUMP,
    TREE_CREW
}

final resourceKindValues = EnumValues({
    "desilting_crew": ResourceKind.DESILTING_CREW,
    "pump": ResourceKind.PUMP,
    "tree_crew": ResourceKind.TREE_CREW
});

enum ResourceStatus {
    EN_ROUTE,
    FREE,
    WORKING
}

final resourceStatusValues = EnumValues({
    "en_route": ResourceStatus.EN_ROUTE,
    "free": ResourceStatus.FREE,
    "working": ResourceStatus.WORKING
});

class Proposal {
    Action action;
    DateTime createdAt;
    DateTime decidedAt;
    String decidedBy;
    String proposalId;
    Agent proposedBy;
    int rank;
    String reason;
    String runId;
    ProposalStatus status;

    Proposal({
        required this.action,
        required this.createdAt,
        required this.decidedAt,
        required this.decidedBy,
        required this.proposalId,
        required this.proposedBy,
        required this.rank,
        required this.reason,
        required this.runId,
        required this.status,
    });

    factory Proposal.fromJson(Map<String, dynamic> json) => Proposal(
        action: Action.fromJson(json["action"]),
        createdAt: DateTime.parse(json["created_at"]),
        decidedAt: DateTime.parse(json["decided_at"]),
        decidedBy: json["decided_by"],
        proposalId: json["proposal_id"],
        proposedBy: agentValues.map[json["proposed_by"]]!,
        rank: json["rank"],
        reason: json["reason"],
        runId: json["run_id"],
        status: proposalStatusValues.map[json["status"]]!,
    );

    Map<String, dynamic> toJson() => {
        "action": action.toJson(),
        "created_at": createdAt.toIso8601String(),
        "decided_at": decidedAt.toIso8601String(),
        "decided_by": decidedBy,
        "proposal_id": proposalId,
        "proposed_by": agentValues.reverse[proposedBy],
        "rank": rank,
        "reason": reason,
        "run_id": runId,
        "status": proposalStatusValues.reverse[status],
    };
}

class Action {
    int buildingsAffected;
    Kind kind;
    List<String> readingIds;
    String resourceId;
    String segmentId;
    List<String> sosIds;
    String messageEn;
    String messageTa;
    int recipientCount;

    Action({
        required this.buildingsAffected,
        required this.kind,
        required this.readingIds,
        required this.resourceId,
        required this.segmentId,
        required this.sosIds,
        required this.messageEn,
        required this.messageTa,
        required this.recipientCount,
    });

    factory Action.fromJson(Map<String, dynamic> json) => Action(
        buildingsAffected: json["buildings_affected"],
        kind: kindValues.map[json["kind"]]!,
        readingIds: List<String>.from(json["reading_ids"].map((x) => x)),
        resourceId: json["resource_id"],
        segmentId: json["segment_id"],
        sosIds: List<String>.from(json["sos_ids"].map((x) => x)),
        messageEn: json["message_en"],
        messageTa: json["message_ta"],
        recipientCount: json["recipient_count"],
    );

    Map<String, dynamic> toJson() => {
        "buildings_affected": buildingsAffected,
        "kind": kindValues.reverse[kind],
        "reading_ids": List<dynamic>.from(readingIds.map((x) => x)),
        "resource_id": resourceId,
        "segment_id": segmentId,
        "sos_ids": List<dynamic>.from(sosIds.map((x) => x)),
        "message_en": messageEn,
        "message_ta": messageTa,
        "recipient_count": recipientCount,
    };
}

enum Kind {
    WARD_ALERT,
    WORK_ORDER
}

final kindValues = EnumValues({
    "ward_alert": Kind.WARD_ALERT,
    "work_order": Kind.WORK_ORDER
});

enum Agent {
    CHRONICLER,
    COMMANDER,
    DISPATCHER,
    HERALD,
    PATHFINDER,
    SENTINEL,
    TRIAGE,
    VERIFIER
}

final agentValues = EnumValues({
    "chronicler": Agent.CHRONICLER,
    "commander": Agent.COMMANDER,
    "dispatcher": Agent.DISPATCHER,
    "herald": Agent.HERALD,
    "pathfinder": Agent.PATHFINDER,
    "sentinel": Agent.SENTINEL,
    "triage": Agent.TRIAGE,
    "verifier": Agent.VERIFIER
});

enum ProposalStatus {
    APPROVED,
    EDITED,
    PENDING,
    REJECTED
}

final proposalStatusValues = EnumValues({
    "approved": ProposalStatus.APPROVED,
    "edited": ProposalStatus.EDITED,
    "pending": ProposalStatus.PENDING,
    "rejected": ProposalStatus.REJECTED
});

class Alert {
    String alertId;
    String messageEn;
    String messageTa;
    
    ///Set for Ward Alerts, which go out only via an approved Proposal.
    String proposalId;
    int recipientCount;
    String runId;
    AlertScope scope;
    List<String> segmentIds;
    DateTime sentAt;

    Alert({
        required this.alertId,
        required this.messageEn,
        required this.messageTa,
        required this.proposalId,
        required this.recipientCount,
        required this.runId,
        required this.scope,
        required this.segmentIds,
        required this.sentAt,
    });

    factory Alert.fromJson(Map<String, dynamic> json) => Alert(
        alertId: json["alert_id"],
        messageEn: json["message_en"],
        messageTa: json["message_ta"],
        proposalId: json["proposal_id"],
        recipientCount: json["recipient_count"],
        runId: json["run_id"],
        scope: alertScopeValues.map[json["scope"]]!,
        segmentIds: List<String>.from(json["segment_ids"].map((x) => x)),
        sentAt: DateTime.parse(json["sent_at"]),
    );

    Map<String, dynamic> toJson() => {
        "alert_id": alertId,
        "message_en": messageEn,
        "message_ta": messageTa,
        "proposal_id": proposalId,
        "recipient_count": recipientCount,
        "run_id": runId,
        "scope": alertScopeValues.reverse[scope],
        "segment_ids": List<dynamic>.from(segmentIds.map((x) => x)),
        "sent_at": sentAt.toIso8601String(),
    };
}

enum AlertScope {
    PLACE,
    WARD
}

final alertScopeValues = EnumValues({
    "place": AlertScope.PLACE,
    "ward": AlertScope.WARD
});

class RouteRequest {
    GeoPoint destination;
    GeoPoint origin;
    String runId;
    VehicleType vehicle;

    RouteRequest({
        required this.destination,
        required this.origin,
        required this.runId,
        required this.vehicle,
    });

    factory RouteRequest.fromJson(Map<String, dynamic> json) => RouteRequest(
        destination: GeoPoint.fromJson(json["destination"]),
        origin: GeoPoint.fromJson(json["origin"]),
        runId: json["run_id"],
        vehicle: vehicleTypeValues.map[json["vehicle"]]!,
    );

    Map<String, dynamic> toJson() => {
        "destination": destination.toJson(),
        "origin": origin.toJson(),
        "run_id": runId,
        "vehicle": vehicleTypeValues.reverse[vehicle],
    };
}

enum VehicleType {
    AMBULANCE,
    CAR,
    TWO_WHEELER
}

final vehicleTypeValues = EnumValues({
    "ambulance": VehicleType.AMBULANCE,
    "car": VehicleType.CAR,
    "two_wheeler": VehicleType.TWO_WHEELER
});

class RouteResponse {
    
    ///Segments the route keeps out of, flooded now or expected to flood before arrival.
    List<String> avoidedSegmentIds;
    double distanceM;
    int durationS;
    
    ///The route. None when status is no_safe_route.
    LineString geometry;
    
    ///One line for the traveller, in English.
    String reason;
    String runId;
    RouteStatus status;

    RouteResponse({
        required this.avoidedSegmentIds,
        required this.distanceM,
        required this.durationS,
        required this.geometry,
        required this.reason,
        required this.runId,
        required this.status,
    });

    factory RouteResponse.fromJson(Map<String, dynamic> json) => RouteResponse(
        avoidedSegmentIds: List<String>.from(json["avoided_segment_ids"].map((x) => x)),
        distanceM: json["distance_m"]?.toDouble(),
        durationS: json["duration_s"],
        geometry: LineString.fromJson(json["geometry"]),
        reason: json["reason"],
        runId: json["run_id"],
        status: routeStatusValues.map[json["status"]]!,
    );

    Map<String, dynamic> toJson() => {
        "avoided_segment_ids": List<dynamic>.from(avoidedSegmentIds.map((x) => x)),
        "distance_m": distanceM,
        "duration_s": durationS,
        "geometry": geometry.toJson(),
        "reason": reason,
        "run_id": runId,
        "status": routeStatusValues.reverse[status],
    };
}

enum RouteStatus {
    NO_SAFE_ROUTE,
    OK
}

final routeStatusValues = EnumValues({
    "no_safe_route": RouteStatus.NO_SAFE_ROUTE,
    "ok": RouteStatus.OK
});

class EnumValues<T> {
    Map<String, T> map;
    late Map<T, String> reverseMap;

    EnumValues(this.map);

    Map<T, String> get reverse {
            reverseMap = map.map((k, v) => MapEntry(v, k));
            return reverseMap;
    }
}
