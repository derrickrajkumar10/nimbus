"""Small helpers for reading and writing contract models in DynamoDB (#42).

Agents use the low-level boto3 client, so tests can wrap it in botocore's Stubber.
Table names come from env vars NIMBUS_TABLE_<NAME>, set on each Lambda from the
SSM parameters NimbusShared publishes (/nimbus/tables/<Name>).
"""

import json
import os
from collections.abc import Iterator
from decimal import Decimal
from typing import Any

from boto3.dynamodb.types import TypeDeserializer, TypeSerializer
from pydantic import BaseModel

_SERIALIZER = TypeSerializer()
_DESERIALIZER = TypeDeserializer()
BATCH_LIMIT = 25


def table_env(table: str) -> str:
    return f"NIMBUS_TABLE_{table.upper()}"


def table_name(table: str) -> str | None:
    return os.environ.get(table_env(table))


def dynamo_client() -> Any:
    import boto3

    return boto3.client("dynamodb")


def to_item(model: BaseModel, **extra: str) -> dict[str, Any]:
    """A contract model as a DynamoDB item. Floats become Decimals, which DynamoDB requires."""
    plain = json.loads(model.model_dump_json(), parse_float=Decimal)
    plain.update(extra)
    return {k: _SERIALIZER.serialize(v) for k, v in plain.items()}


def _undecimal(value: Any) -> Any:
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, list):
        return [_undecimal(v) for v in value]
    if isinstance(value, dict):
        return {k: _undecimal(v) for k, v in value.items()}
    return value


def from_item(item: dict[str, Any]) -> dict[str, Any]:
    return {k: _undecimal(_DESERIALIZER.deserialize(v)) for k, v in item.items()}


def query_all(client: Any, **kwargs: Any) -> Iterator[dict[str, Any]]:
    """Every item of a Query, following pagination."""
    while True:
        page = client.query(**kwargs)
        yield from page.get("Items", [])
        if "LastEvaluatedKey" not in page:
            return
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]


def put_all(client: Any, table: str, items: list[dict[str, Any]], max_retries: int = 5) -> None:
    """BatchWriteItem in chunks of 25, retrying unprocessed items."""
    for start in range(0, len(items), BATCH_LIMIT):
        requests = {table: [{"PutRequest": {"Item": item}} for item in items[start : start + BATCH_LIMIT]]}
        for _ in range(max_retries + 1):
            unprocessed = client.batch_write_item(RequestItems=requests).get("UnprocessedItems") or {}
            if not unprocessed:
                break
            requests = unprocessed
        else:
            raise RuntimeError(f"DynamoDB left {len(unprocessed.get(table, []))} items unwritten in {table}")
