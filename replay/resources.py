"""Resources seeding for a Replay Run: the pumps and crews the Dispatcher can send.

Every Run starts from the same Resources (contracts/fixtures/resources.json) with
run_id rewritten to the Run's id. Items are the Resource as model_dump(mode="json"),
keyed by run_id and resource_id, so seeding a Run twice writes the same rows and
resets their status.
"""

import json
import os
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Any

from boto3.dynamodb.types import TypeSerializer
from nimbus_contracts.entities import Resource

from dynamo import batch_put

TABLE_PARAM = "/nimbus/tables/Resources"
TABLE_ENV = "NIMBUS_TABLE_RESOURCES"
FIXTURE = Path(__file__).resolve().parents[1] / "contracts" / "fixtures" / "resources.json"

_SERIALIZER = TypeSerializer()


def for_run(run_id: str, fixture: Path = FIXTURE) -> list[Resource]:
    return [
        Resource.model_validate({**row, "run_id": run_id}) for row in json.loads(fixture.read_text())
    ]


def item(resource: Resource) -> dict[str, Any]:
    """The Resource as a DynamoDB item. Floats become Decimals, which DynamoDB requires."""
    plain = json.loads(json.dumps(resource.model_dump(mode="json")), parse_float=Decimal)
    return {key: _SERIALIZER.serialize(value) for key, value in plain.items()}


def table_name(ssm: Callable[[], Any]) -> str:
    """The env override if set, else the SSM parameter. `ssm` makes the client, only when it's needed."""
    return os.environ.get(TABLE_ENV) or ssm().get_parameter(Name=TABLE_PARAM)["Parameter"]["Value"]


def write(client: Any, table: str, resources: list[Resource], **kwargs: Any) -> None:
    batch_put(client, table, [item(r) for r in resources], what="Resources", **kwargs)
