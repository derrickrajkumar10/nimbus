"""SegmentRisk in DynamoDB (#42): the Sentinel is its single writer (#32), the Herald reads it.

Keys per contracts/storage.md: partition `run_id`, sort `segment_id`, latest only.
"""

from collections.abc import Sequence
from typing import Any

from nimbus_contracts.entities import SegmentRisk

from common.dynamo import dynamo_client, from_item, put_all, query_all, table_name, to_item


class DynamoRiskStore:
    def __init__(self, table: str, client: Any = None) -> None:
        self.table = table
        self._client = client

    @classmethod
    def from_env(cls) -> "DynamoRiskStore | None":
        name = table_name("SegmentRisk")
        return cls(name) if name else None

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = dynamo_client()
        return self._client

    def latest(self, run_id: str) -> dict[str, SegmentRisk]:
        items = query_all(
            self.client,
            TableName=self.table,
            KeyConditionExpression="run_id = :run",
            ExpressionAttributeValues={":run": {"S": run_id}},
        )
        risks = (SegmentRisk.model_validate(from_item(item)) for item in items)
        return {r.segment_id: r for r in risks}

    def save(self, risks: Sequence[SegmentRisk]) -> None:
        if risks:
            put_all(self.client, self.table, [to_item(r) for r in risks])
