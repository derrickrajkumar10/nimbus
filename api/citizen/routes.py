"""The Flutter app's HTTP routes (issue #7, the M1 subset).

An install is identified by the `X-Install-Id` header until Cognito guest identities arrive with
issue #19. Anyone can claim any id until then, so nothing here is private. Reports, SOS and routes
come next (#7b).
"""

import logging
import re
from typing import Annotated, Any, Literal

from nimbus_contracts.common import GeoPoint, RunId
from nimbus_contracts.entities import Reading, SavedPlace, SavedPlaceKind, Segment, SegmentRisk
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from citizen.geo import covered_segment_ids
from citizen.store import Store
from console.http import HttpError, Request, Router

log = logging.getLogger(__name__)

INSTALL_ID = re.compile(r"^[A-Za-z0-9:_-]{8,80}$")  # Cognito identity ids contain ':' ("us-east-1:<uuid>")
PLACE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
MAX_PLACES_PER_DEVICE = 20
_RUN_ID = TypeAdapter(RunId)


class DeviceRegistration(BaseModel):
    """Body of POST /devices."""

    model_config = ConfigDict(extra="forbid")

    fcm_token: Annotated[str, Field(min_length=10, max_length=4096)]
    language: Literal["en", "ta"]


class SavedPlaceRequest(BaseModel):
    """Body of PUT /saved-places/{place_id}. The server works out `segment_ids`."""

    model_config = ConfigDict(extra="forbid")

    label: Annotated[str, Field(min_length=1, max_length=60)]
    kind: SavedPlaceKind
    location: GeoPoint
    radius_m: Annotated[float, Field(gt=0, le=1000)] = 150
    run_ids: Annotated[
        list[RunId],
        Field(min_length=1, max_length=3, description="Runs to alert this place in. Demo phones add their Replay."),
    ] = ["live"]


class Citizen:
    def __init__(self, store: Store) -> None:
        self.store = store
        self._segments: list[dict[str, Any]] | None = None
        self.router = Router()
        self.router.add("GET", "/segments", self.segments)
        self.router.add("GET", "/risk", self.risk)
        self.router.add("GET", "/readings", self.readings)
        self.router.add("POST", "/devices", self.register_device)
        self.router.add("GET", "/saved-places", self.list_places)
        self.router.add("PUT", "/saved-places/{place_id}", self.put_place)
        self.router.add("DELETE", "/saved-places/{place_id}", self.delete_place)

    def handle(self, event: dict[str, Any]) -> dict[str, Any]:
        return self.router.handle(event)

    # --- helpers ---------------------------------------------------------------

    @staticmethod
    def install_id(request: Request) -> str:
        value = request.headers.get("x-install-id", "")
        if not INSTALL_ID.match(value):
            raise HttpError(401, "install_id_required", "send your app install's id in the X-Install-Id header")
        return value

    @staticmethod
    def run_id(request: Request) -> str:
        raw = request.query.get("run_id")
        if not raw:
            raise HttpError(400, "run_id_required", "run_id is required: every request is scoped to one Run")
        try:
            return _RUN_ID.validate_python(raw)
        except ValidationError as error:
            raise HttpError(400, "invalid_run_id", f"run_id must be 'live' or 'replay-<name>', got {raw!r}") from error

    def _segment_rows(self) -> list[dict[str, Any]]:
        """Segments are static, so they're read once and kept while the Lambda stays warm."""
        if self._segments is None:
            self._segments = [Segment.model_validate(row).model_dump(mode="json") for row in self.store.scan("Segments")]
        return self._segments

    # --- reads -----------------------------------------------------------------

    def segments(self, request: Request) -> list[dict[str, Any]]:
        return self._segment_rows()

    def risk(self, request: Request) -> list[dict[str, Any]]:
        rows = self.store.query("SegmentRisk", self.run_id(request))
        return [SegmentRisk.model_validate(r).model_dump(mode="json") for r in rows]

    def readings(self, request: Request) -> list[dict[str, Any]]:
        """Readings of a Run, or only those merged from `report_id` (the app polls this after a photo)."""
        report_id = request.query.get("report_id")
        readings = [Reading.model_validate(r) for r in self.store.query("Readings", self.run_id(request))]
        return [r.model_dump(mode="json") for r in readings if report_id is None or report_id in r.report_ids]

    # --- this install's device and places -------------------------------------

    def register_device(self, request: Request) -> dict[str, Any]:
        device_id = self.install_id(request)
        body = self._body(DeviceRegistration, request)
        self.store.put("Devices", {"device_id": device_id, "fcm_token": body.fcm_token, "language": body.language})
        return {"device_id": device_id, "language": body.language}

    def list_places(self, request: Request) -> list[dict[str, Any]]:
        return [self._view(row) for row in self.store.query("SavedPlaces", self.install_id(request))]

    def put_place(self, request: Request) -> dict[str, Any]:
        device_id, place_id = self.install_id(request), self._place_id(request)
        body = self._body(SavedPlaceRequest, request)

        existing = self.store.get("SavedPlaces", device_id, place_id)
        if existing is None and len(self.store.query("SavedPlaces", device_id)) >= MAX_PLACES_PER_DEVICE:
            raise HttpError(409, "too_many_places", f"an install can save at most {MAX_PLACES_PER_DEVICE} places")

        segment_ids = covered_segment_ids(body.location.lat, body.location.lon, body.radius_m, self._segment_rows())
        place = SavedPlace(
            place_id=place_id,
            device_id=device_id,
            label=body.label,
            kind=body.kind,
            location=body.location,
            radius_m=body.radius_m,
            segment_ids=segment_ids,
        )
        item = place.model_dump(mode="json") | {"run_ids": list(body.run_ids)}
        self.store.put("SavedPlaces", item)  # the place first, then the index, then retire stale entries
        new = self._index_pairs(item)
        for run_id, segment_id in sorted(new):
            self.store.put("PlaceIndex", self._index_row(run_id, segment_id, device_id, place_id))
        if existing:
            for run_id, segment_id in sorted(self._index_pairs(existing) - new):
                self.store.delete("PlaceIndex", f"{run_id}#{segment_id}", f"{device_id}#{place_id}")
        return self._view(item)

    def delete_place(self, request: Request) -> dict[str, Any]:
        device_id, place_id = self.install_id(request), self._place_id(request)
        existing = self.store.get("SavedPlaces", device_id, place_id)
        if existing is None:
            raise HttpError(404, "place_not_found", f"no Saved Place {place_id}")
        for run_id, segment_id in sorted(self._index_pairs(existing)):
            self.store.delete("PlaceIndex", f"{run_id}#{segment_id}", f"{device_id}#{place_id}")
        self.store.delete("SavedPlaces", device_id, place_id)
        return {"deleted": place_id}

    # --- internals -------------------------------------------------------------

    @staticmethod
    def _place_id(request: Request) -> str:
        place_id = request.params["place_id"]
        if not PLACE_ID.match(place_id):
            raise HttpError(400, "invalid_place_id", "place_id may use letters, digits, '_' and '-' (64 at most)")
        return place_id

    @staticmethod
    def _body(model: type[BaseModel], request: Request) -> Any:
        try:
            return model.model_validate(request.json())
        except ValidationError as error:
            raise HttpError(
                422, "invalid_body", "the request body is invalid",
                details=error.errors(include_url=False, include_context=False, include_input=False),
            ) from error

    @staticmethod
    def _index_pairs(row: dict[str, Any]) -> set[tuple[str, str]]:
        return {(run, seg) for run in row.get("run_ids", ["live"]) for seg in row.get("segment_ids", [])}

    @staticmethod
    def _index_row(run_id: str, segment_id: str, device_id: str, place_id: str) -> dict[str, str]:
        return {"run_id#segment_id": f"{run_id}#{segment_id}", "device_id#place_id": f"{device_id}#{place_id}"}

    @staticmethod
    def _view(row: dict[str, Any]) -> dict[str, Any]:
        """A Saved Place as the contract has it, plus the Runs it alerts in."""
        place = SavedPlace.model_validate({k: v for k, v in row.items() if k != "run_ids"})
        return place.model_dump(mode="json") | {"run_ids": row.get("run_ids", ["live"])}
