"""The tables the citizen API reads and writes, and a fake for tests.

Keys are from contracts/storage.md. A composite key such as `run_id#segment_id` is one attribute
with that literal name, holding values like "replay-michaung#27480309-1".
"""

import json
import os
from decimal import Decimal
from typing import Any, Protocol

from console.store import plain

TABLE_KEYS: dict[str, tuple[str, str | None]] = {
    "Segments": ("segment_id", None),
    "SegmentRisk": ("run_id", "segment_id"),
    "Readings": ("run_id", "reading_id"),
    "Reports": ("run_id", "report_id"),
    "Activity": ("run_id", "emitted_at#event_id"),
    "Runs": ("run_id", None),
    "Devices": ("device_id", None),
    "SavedPlaces": ("device_id", "place_id"),
    "PlaceIndex": ("run_id#segment_id", "device_id#place_id"),
}
TABLE_ENV_PREFIX = "NIMBUS_TABLE_"


class Store(Protocol):
    def scan(self, table: str) -> list[dict[str, Any]]: ...
    def query(self, table: str, pk: str, *, newest_first: bool = False, limit: int | None = None) -> list[dict[str, Any]]: ...
    def get(self, table: str, pk: str, sk: str | None = None) -> dict[str, Any] | None: ...
    def put(self, table: str, item: dict[str, Any], *, only_if_absent: bool = False) -> bool:
        """Write `item`. With `only_if_absent`, False when a row with that key already exists."""
        ...
    def delete(self, table: str, pk: str, sk: str | None = None) -> None: ...


class MemoryStore:
    def __init__(self) -> None:
        self.tables: dict[str, dict[tuple[str, str | None], dict[str, Any]]] = {t: {} for t in TABLE_KEYS}

    def _key(self, table: str, row: dict[str, Any]) -> tuple[str, str | None]:
        pk, sk = TABLE_KEYS[table]
        return row[pk], (row[sk] if sk else None)

    def scan(self, table):
        return [dict(r) for r in self.tables[table].values()]

    def query(self, table, pk, *, newest_first=False, limit=None):
        rows = [r for (p, _), r in self.tables[table].items() if p == pk]
        sk = TABLE_KEYS[table][1]
        if sk:
            rows = sorted(rows, key=lambda r: r[sk], reverse=newest_first)
        return [dict(r) for r in (rows[:limit] if limit else rows)]

    def get(self, table, pk, sk=None):
        row = self.tables[table].get((pk, sk))
        return dict(row) if row else None

    def put(self, table, item, *, only_if_absent=False):
        key = self._key(table, item)
        if only_if_absent and key in self.tables[table]:
            return False
        self.tables[table][key] = dict(item)
        return True

    def delete(self, table, pk, sk=None):
        self.tables[table].pop((pk, sk), None)


class DynamoStore:
    """`resource` is a boto3 dynamodb resource. Names come from NIMBUS_TABLE_<TABLE> unless `table_names` is given."""

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

    def _key(self, table: str, pk: str, sk: str | None) -> dict[str, str]:
        pk_name, sk_name = TABLE_KEYS[table]
        return {pk_name: pk} | ({sk_name: sk} if sk_name else {})

    def _all(self, method: str, table: str, **kwargs: Any) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        while True:
            page = getattr(self._table(table), method)(**kwargs)
            rows.extend(plain(item) for item in page.get("Items", []))
            if "LastEvaluatedKey" not in page:
                return rows
            kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]

    def scan(self, table):
        return self._all("scan", table)

    def query(self, table, pk, *, newest_first=False, limit=None):
        from boto3.dynamodb.conditions import Key

        kwargs: dict[str, Any] = {
            "KeyConditionExpression": Key(TABLE_KEYS[table][0]).eq(pk),
            "ScanIndexForward": not newest_first,
        }
        if limit:
            kwargs["Limit"] = limit
            return [plain(i) for i in self._table(table).query(**kwargs).get("Items", [])]
        return self._all("query", table, **kwargs)

    def get(self, table, pk, sk=None):
        item = self._table(table).get_item(Key=self._key(table, pk, sk)).get("Item")
        return plain(item) if item else None

    def put(self, table, item, *, only_if_absent=False):
        from boto3.dynamodb.conditions import Attr
        from botocore.exceptions import ClientError

        kwargs: dict[str, Any] = {"Item": json.loads(json.dumps(item), parse_float=Decimal)}
        if only_if_absent:
            kwargs["ConditionExpression"] = Attr(TABLE_KEYS[table][0]).not_exists()
        try:
            self._table(table).put_item(**kwargs)
            return True
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                return False
            raise

    def delete(self, table, pk, sk=None):
        self._table(table).delete_item(Key=self._key(table, pk, sk))
