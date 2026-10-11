"""Safe-route request and response, shared by the citizen API, the Pathfinder and the app.

`POST /routes` takes a RouteRequest and returns a RouteResponse. The router (ADR 0003)
checks Amazon Location's violation notices, and when a route would still cross a
no-go zone the answer is `no_safe_route`, never a route through it.
"""

from enum import StrEnum
from typing import Annotated

from pydantic import Field, model_validator

from .common import Contract, GeoPoint, LineString, RunId, SegmentId, VehicleType


class RouteStatus(StrEnum):
    OK = "ok"
    NO_SAFE_ROUTE = "no_safe_route"


class RouteRequest(Contract):
    run_id: RunId
    origin: GeoPoint
    destination: GeoPoint
    vehicle: VehicleType


class RouteResponse(Contract):
    run_id: RunId
    status: RouteStatus
    geometry: Annotated[LineString | None, Field(description="The route. None when status is no_safe_route.")] = None
    distance_m: Annotated[float | None, Field(ge=0)] = None
    duration_s: Annotated[int | None, Field(ge=0)] = None
    avoided_segment_ids: Annotated[
        list[SegmentId], Field(description="Segments the route keeps out of, flooded now or expected to flood before arrival.")
    ] = []
    avoided_hazard_ids: Annotated[
        list[str], Field(description="Hazards (open manholes, live wires) the route keeps clear of.")
    ] = []
    reason: Annotated[
        str,
        Field(
            description="One line for the traveller, in English.",
            examples=["Avoids 2 streets reported knee-deep."],
        ),
    ]
    reason_ta: Annotated[str | None, Field(description="The same line in Tamil, when the Pathfinder has one.")] = None

    @model_validator(mode="after")
    def _status_matches_route(self) -> "RouteResponse":
        has_route = self.geometry is not None
        if self.status == RouteStatus.OK and not (has_route and self.distance_m is not None and self.duration_s is not None):
            raise ValueError("an ok route needs geometry, distance_m and duration_s")
        if self.status == RouteStatus.NO_SAFE_ROUTE and (has_route or self.distance_m is not None or self.duration_s is not None):
            raise ValueError("no_safe_route must not carry a route")
        return self
