"""The generated Dart models must accept every value the contracts allow.

Dart has no test runner in CI, so this reads generated/dart/nimbus.dart as text.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "schema" / "nimbus.schema.json").read_text())
DART = (ROOT / "generated" / "dart" / "nimbus.dart").read_text()
DART_MODELS = re.search(r"\bfor m in ([\w ]+);", (ROOT / "generate.sh").read_text()).group(1).split()


def _camel(name: str) -> str:
    head, *rest = name.split("_")
    return head + "".join(part.title() for part in rest)


def _nullable(prop: dict) -> bool:
    return any(option.get("type") == "null" for option in prop.get("anyOf", []))


def _class_body(model: str) -> str:
    match = re.search(rf"^class {model} \{{(.*?)^\}}", DART, re.S | re.M)
    assert match, f"no Dart class {model}"
    return match.group(1)


def test_nullable_contract_fields_are_nullable_in_dart():
    missing = []
    for model in DART_MODELS:
        body = _class_body(model)
        for name, prop in SCHEMA["$defs"][model]["properties"].items():
            if _nullable(prop) and not re.search(rf"\?\s+{_camel(name)};", body):
                missing.append(f"{model}.{name}")
    assert not missing, f"nullable in the contract but not in Dart: {missing}"


def test_risk_fixture_has_nulls_the_dart_model_must_take():
    rows = json.loads((ROOT / "fixtures" / "risk.json").read_text())
    assert any(row["minutes_to_flood"] is None for row in rows)
