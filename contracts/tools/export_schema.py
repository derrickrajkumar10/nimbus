"""Write JSON Schema for every contract to schema/. Other languages generate types from these.

    uv run python tools/export_schema.py            # write
    uv run python tools/export_schema.py --check    # fail if schema/ is stale
"""

import json
import sys
from pathlib import Path

from pydantic import TypeAdapter
from pydantic.json_schema import models_json_schema

from nimbus_contracts import entities, routes
from nimbus_contracts.events import EVENT_TYPES, Event

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "schema"

ENTITIES = [
    entities.Segment,
    entities.SegmentRisk,
    entities.Report,
    entities.Reading,
    entities.Hazard,
    entities.Sos,
    entities.RankedSos,
    entities.SavedPlace,
    entities.Resource,
    entities.Proposal,
    entities.Alert,
    routes.RouteRequest,
    routes.RouteResponse,
]


def schemas() -> dict[str, dict]:
    out = {f"{m.__name__}.schema.json": m.model_json_schema() for m in ENTITIES}
    out |= {f"events/{m.model_fields['type'].default}.schema.json": m.model_json_schema() for m in EVENT_TYPES}
    out["events/Event.schema.json"] = TypeAdapter(Event).json_schema() | {"title": "Event"}
    out["nimbus.schema.json"] = bundle()
    return {name: s | {"$schema": "https://json-schema.org/draft/2020-12/schema"} for name, s in out.items()}


def bundle() -> dict:
    """Every contract in one file under $defs, with Event as a discriminated union. Input for TypeScript."""
    _, schema = models_json_schema([(m, "validation") for m in ENTITIES + EVENT_TYPES], title="Nimbus")
    defs = schema["$defs"]
    defs["Event"] = {
        "title": "Event",
        "oneOf": [{"$ref": f"#/$defs/{m.__name__}"} for m in EVENT_TYPES],
        "discriminator": {"propertyName": "type"},
    }
    return {"title": "Nimbus", "$defs": defs}


def main(check: bool) -> int:
    stale = []
    for name, schema in schemas().items():
        path = OUT / name
        text = json.dumps(schema, indent=2, ensure_ascii=False) + "\n"
        if check:
            if not path.exists() or path.read_text() != text:
                stale.append(name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
    if stale:
        print("Stale schema, run tools/export_schema.py:", *stale, sep="\n  ")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
