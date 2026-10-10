"""Small domain rules more than one lane needs. Change them here, not in a copy."""

from .common import DEPTH_ORDER, DepthBand, RiskBand, VehicleType

# Risk Score cut-offs. The score alone never yields "flooded"; only a Reading does.
WATCH_FROM = 40
LIKELY_FROM = 70


def band_for_score(score: int) -> RiskBand:
    if score >= LIKELY_FROM:
        return RiskBand.LIKELY
    if score >= WATCH_FROM:
        return RiskBand.WATCH
    return RiskBand.LOW


# Deepest water each vehicle profile can pass. Configurable on purpose: these are judgement calls.
MAX_PASSABLE_DEPTH: dict[VehicleType, DepthBand] = {
    VehicleType.TWO_WHEELER: DepthBand.ANKLE,
    VehicleType.CAR: DepthBand.ANKLE,
    VehicleType.AMBULANCE: DepthBand.KNEE,
}

# Amazon Location Routes v2 travel mode per profile (ADR 0003).
TRAVEL_MODE: dict[VehicleType, str] = {
    VehicleType.TWO_WHEELER: "Scooter",
    VehicleType.CAR: "Car",
    VehicleType.AMBULANCE: "Car",
}


def can_pass(vehicle: VehicleType, depth: DepthBand) -> bool:
    return DEPTH_ORDER.index(depth) <= DEPTH_ORDER.index(MAX_PASSABLE_DEPTH[vehicle])
