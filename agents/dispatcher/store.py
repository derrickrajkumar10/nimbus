"""What the Dispatcher reads and writes in DynamoDB, with in-memory stand-ins for local runs.

- Resources (contracts/storage.md: `run_id`, `resource_id`): the Dispatcher's table. The
  Replay Driver seeds each Run; the Dispatcher sets `en_route` on an approved Work Order.
- Proposals (`run_id`, `proposal_id`): read only. The projector writes them (#32); the
  Dispatcher reads its own to avoid proposing the same Resource or Segment twice.
"""

from collections.abc import Sequence
from typing import Any

from nimbus_contracts.entities import Proposal, Resource, ResourceStatus

from common.dynamo import dynamo_client, from_item, query_all, table_name


class MemoryResources:
    """In-memory Resources. With a `template`, each new Run starts with a copy of it, as the Replay Driver seeds."""

    def __init__(self, resources: Sequence[Resource] = (), template: Sequence[Resource] = ()) -> None:
        self._rows = {(r.run_id, r.resource_id): r for r in resources}
        self._template = tuple(template)

    def for_run(self, run_id: str) -> list[Resource]:
        if self._template and not any(run == run_id for run, _ in self._rows):
            for r in self._template:
                self._rows[(run_id, r.resource_id)] = r.model_copy(update={"run_id": run_id})
        return [r for (run, _), r in sorted(self._rows.items()) if run == run_id]

    def set_status(self, run_id: str, resource_id: str, status: ResourceStatus) -> bool:
        row = self._rows.get((run_id, resource_id))
        if row is None:
            return False
        self._rows[(run_id, resource_id)] = row.model_copy(update={"status": status})
        return True


class MemoryProposals:
    def __init__(self) -> None:
        self.rows: list[Proposal] = []

    def by_agent(self, run_id: str, agent: str) -> list[Proposal]:
        return [p for p in self.rows if p.run_id == run_id and p.proposed_by == agent]


class _Table:
    def __init__(self, table: str, client: Any = None) -> None:
        self.table = table
        self._client = client

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = dynamo_client()
        return self._client

    def _query(self, run_id: str) -> list[dict[str, Any]]:
        items = query_all(
            self.client,
            TableName=self.table,
            KeyConditionExpression="run_id = :run",
            ExpressionAttributeValues={":run": {"S": run_id}},
        )
        return [from_item(item) for item in items]


class DynamoResources(_Table):
    @classmethod
    def from_env(cls) -> "DynamoResources | None":
        name = table_name("Resources")
        return cls(name) if name else None

    def for_run(self, run_id: str) -> list[Resource]:
        return [Resource.model_validate(row) for row in self._query(run_id)]

    def set_status(self, run_id: str, resource_id: str, status: ResourceStatus) -> bool:
        """Only an existing row: a Resource that was never seeded stays absent."""
        try:
            self.client.update_item(
                TableName=self.table,
                Key={"run_id": {"S": run_id}, "resource_id": {"S": resource_id}},
                UpdateExpression="SET #s = :s",
                ConditionExpression="attribute_exists(resource_id)",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={":s": {"S": status.value}},
            )
        except self.client.exceptions.ConditionalCheckFailedException:
            return False
        return True


class DynamoProposals(_Table):
    @classmethod
    def from_env(cls) -> "DynamoProposals | None":
        name = table_name("Proposals")
        return cls(name) if name else None

    def by_agent(self, run_id: str, agent: str) -> list[Proposal]:
        return [Proposal.model_validate(row) for row in self._query(run_id) if row.get("proposed_by") == agent]
