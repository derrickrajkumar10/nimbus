"""The tables the console reads, and the one row it updates (a Proposal's decision).

Every read is a Query on the Run's partition, so a request can't see another Run's rows
(ADR 0001). `MemoryStore` stands in for DynamoDB in tests.
"""

import json
import os
from decimal import Decimal
from typing import Any, Protocol

# Table -> (partition key, sort key or None), as in contracts/storage.md. tests/test_console.py checks it.
TABLE_KEYS: dict[str, tuple[str, str | None]] = {
    "SegmentRisk": ("run_id", "segment_id"),
    "Readings": ("run_id", "reading_id"),
    "Hazards": ("run_id", "hazard_id"),
    "Resources": ("run_id", "resource_id"),
    "Sos": ("run_id", "sos_id"),
    "Proposals": ("run_id", "proposal_id"),
    "Activity": ("run_id", "emitted_at#event_id"),
    "Runs": ("run_id", None),
}

TABLE_ENV_PREFIX = "NIMBUS_TABLE_"


class Store(Protocol):
    def query(
        self, table: str, run_id: str, *, after: str | None = None, limit: int | None = None, newest_first: bool = False
    ) -> list[dict[str, Any]]:
        """Rows of `run_id` in sort-key order (descending with `newest_first`).

        `after` is an exclusive lower bound on the sort key.
        """
        ...

    def get(self, table: str, run_id: str, sort: str | None = None) -> dict[str, Any] | None: ...

    def update_proposal(self, run_id: str, proposal_id: str, values: dict[str, Any], *, only_if_status: str | None) -> bool:
        """Set `values` on a Proposal. False when `only_if_status` no longer holds or the row is missing."""
        ...


def plain(value: Any) -> Any:
    """DynamoDB Decimals back to int or float, so the row is JSON-able."""
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, list):
        return [plain(v) for v in value]
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    return value


class MemoryStore:
    def __init__(self) -> None:
        self.tables: dict[str, dict[tuple[str, str | None], dict[str, Any]]] = {name: {} for name in TABLE_KEYS}

    def put(self, table: str, row: dict[str, Any]) -> None:
        pk, sk = TABLE_KEYS[table]
        self.tables[table][(row[pk], row[sk] if sk else None)] = dict(row)

    def query(self, table, run_id, *, after=None, limit=None, newest_first=False):
        _, sk = TABLE_KEYS[table]
        rows = [row for (pk, _), row in self.tables[table].items() if pk == run_id]
        if sk:
            rows.sort(key=lambda r: r[sk], reverse=newest_first)
            if after is not None:
                rows = [r for r in rows if r[sk] > after]
        return [dict(r) for r in (rows[:limit] if limit else rows)]

    def get(self, table, run_id, sort=None):
        row = self.tables[table].get((run_id, sort))
        return dict(row) if row else None

    def update_proposal(self, run_id, proposal_id, values, *, only_if_status):
        row = self.tables["Proposals"].get((run_id, proposal_id))
        if row is None or (only_if_status is not None and row.get("status") != only_if_status):
            return False
        row.update(values)
        return True


class DynamoStore:
    """Reads and updates the NimbusShared tables. `resource` is a boto3 dynamodb resource."""

    def __init__(self, resource: Any = None, table_names: dict[str, str] | None = None) -> None:
        self._resource = resource
        self._names = table_names

    @property
    def resource(self) -> Any:
        if self._resource is None:
            import boto3

            self._resource = boto3.resource("dynamodb")
        return self._resource

    def _table(self, table: str) -> Any:
        name = self._names[table] if self._names else os.environ[TABLE_ENV_PREFIX + table.upper()]
        return self.resource.Table(name)

    def query(self, table, run_id, *, after=None, limit=None, newest_first=False):
        from boto3.dynamodb.conditions import Key

        pk, sk = TABLE_KEYS[table]
        condition = Key(pk).eq(run_id)
        if sk and after is not None:
            condition = condition & Key(sk).gt(after)
        kwargs: dict[str, Any] = {"KeyConditionExpression": condition, "ScanIndexForward": not newest_first}
        rows: list[dict[str, Any]] = []
        while True:
            if limit:
                kwargs["Limit"] = limit - len(rows)
            page = self._table(table).query(**kwargs)
            rows.extend(plain(item) for item in page.get("Items", []))
            if "LastEvaluatedKey" not in page or (limit and len(rows) >= limit):
                return rows
            kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]

    def get(self, table, run_id, sort=None):
        pk, sk = TABLE_KEYS[table]
        key = {pk: run_id} | ({sk: sort} if sk else {})
        item = self._table(table).get_item(Key=key).get("Item")
        return plain(item) if item else None

    def update_proposal(self, run_id, proposal_id, values, *, only_if_status):
        from boto3.dynamodb.conditions import Attr
        from botocore.exceptions import ClientError

        values = json.loads(json.dumps(values), parse_float=Decimal)  # floats must be Decimal
        names = {f"#a{i}": k for i, k in enumerate(values)}
        condition = Attr("run_id").exists()
        if only_if_status is not None:
            condition = condition & Attr("status").eq(only_if_status)
        try:
            self._table("Proposals").update_item(
                Key={"run_id": run_id, "proposal_id": proposal_id},
                UpdateExpression="SET " + ", ".join(f"#a{i} = :v{i}" for i in range(len(values))),
                ExpressionAttributeNames=names,
                ExpressionAttributeValues={f":v{i}": v for i, v in enumerate(values.values())},
                ConditionExpression=condition,
            )
            return True
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                return False
            raise
