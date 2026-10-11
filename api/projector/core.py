"""Copy bus events into the DynamoDB tables the console and app read.

Agents publish contract events and never write these tables (api/README.md, issue #32).
`project(event)` turns one event into table writes and does no I/O; a Store applies them.
A table has one writer: events that something else owns (`risk.changed`, `report.created`,
`proposal.decided`, `clock.tick`) are deliberately not projected.

Every key leads with the event's `run_id` (ADR 0001), and EventBridge delivers at least
once, so a redelivered event must change nothing.
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol

from nimbus_contracts.events import EVENT_TYPES, Event
from pydantic import BaseModel, TypeAdapter

log = logging.getLogger(__name__)

_EVENT = TypeAdapter(Event)

# Table -> (partition key, sort key), as in contracts/storage.md. tests/test_projector.py checks it.
KEYS: dict[str, tuple[str, str]] = {
    "Activity": ("run_id", "emitted_at#event_id"),
    "Proposals": ("run_id", "proposal_id"),
    "Alerts": ("run_id", "alert_id"),
    "Hazards": ("run_id", "hazard_id"),
    "Readings": ("run_id", "reading_id"),
    "Sos": ("run_id", "sos_id"),
}

PROJECTED = {
    "agent.activity",
    "policy.decided",
    "proposal.created",
    "alert.sent",
    "hazard.detected",
    "report.verified",
    "sos.created",
    "sos.ranked",
}
# Written by their owner instead (api/README.md). Listed so a new event type has to be classified.
NOT_PROJECTED = {
    "clock.tick",  # Runs belongs to the Replay Driver
    "risk.changed",  # SegmentRisk belongs to the Sentinel; the event can't rebuild the row
    "report.created",  # the API wrote the Report before emitting this
    "proposal.decided",  # the API route updates the Proposal, conditionally on pending
}

TABLE_ENV_PREFIX = "NIMBUS_TABLE_"  # NIMBUS_TABLE_ACTIVITY, set on the Lambda from NimbusShared


def utc_key(dt: datetime) -> str:
    """`dt` as a fixed-width UTC sort key. Same format as agents/common/keys.py `utc_key`.

    The event's own JSON drops a zero fraction ("07:00:00Z"), so as text it sorts after
    "07:00:00.500000Z" although it is earlier.
    """
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"sort-key times must be timezone-aware, got naive {dt.isoformat()}")
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


@dataclass(frozen=True)
class Put:
    table: str
    item: dict[str, Any]
    only_if_absent: bool = False  # a redelivery must not overwrite a row that has moved on


@dataclass(frozen=True)
class Update:
    table: str
    key: dict[str, str]
    values: dict[str, Any]  # attributes to set; the row must already exist


Write = Put | Update


def _item(model: BaseModel) -> dict[str, Any]:
    """The model as DynamoDB-ready JSON: floats become Decimal, which boto3 requires."""
    return json.loads(model.model_dump_json(), parse_float=Decimal)


def parse_eventbridge(payload: dict[str, Any]) -> Any:
    """The contract event inside an EventBridge envelope. Raises if it isn't a valid one."""
    event = _EVENT.validate_python(payload["detail"])
    if payload.get("detail-type") != event.type:
        raise ValueError(f"detail-type {payload.get('detail-type')!r} does not match event type {event.type!r}")
    return event


def project(event: Any) -> list[Write]:
    """The table writes for `event`, none for events another lane owns."""
    run_id = event.run_id
    match event.type:
        case "agent.activity" | "policy.decided":
            item = _item(event)
            item["emitted_at#event_id"] = f"{utc_key(event.emitted_at)}#{event.event_id}"
            return [Put("Activity", item)]
        case "proposal.created":
            return [Put("Proposals", _item(event.detail), only_if_absent=True)]
        case "alert.sent":
            return [Put("Alerts", _item(event.detail))]
        case "hazard.detected":
            return [Put("Hazards", _item(event.detail))]
        case "report.verified":
            return [Put("Readings", _item(event.detail))]
        case "sos.created":
            # only_if_absent: a redelivery after sos.ranked must not wipe the ranking.
            return [Put("Sos", _item(event.detail), only_if_absent=True)]
        case "sos.ranked":
            return [
                Update(
                    "Sos",
                    key={"run_id": run_id, "sos_id": ranked.sos_id},
                    values={k: v for k, v in _item(ranked).items() if k != "sos_id"},
                )
                for ranked in event.detail.ranking
            ]
        case _:
            return []


class Store(Protocol):
    def apply(self, write: Write) -> bool:
        """Apply one write. False when its condition said it had already been done or the row is missing."""
        ...


class MemoryStore:
    """A fake store for tests: rows keyed by (partition key, sort key)."""

    def __init__(self) -> None:
        self.tables: dict[str, dict[tuple[str, str], dict[str, Any]]] = {name: {} for name in KEYS}

    def rows(self, table: str) -> list[dict[str, Any]]:
        return list(self.tables[table].values())

    def apply(self, write: Write) -> bool:
        pk, sk = KEYS[write.table]
        rows = self.tables[write.table]
        if isinstance(write, Put):
            key = (write.item[pk], write.item[sk])
            if write.only_if_absent and key in rows:
                return False
            rows[key] = dict(write.item)
            return True
        key = (write.key[pk], write.key[sk])
        if key not in rows:
            return False
        rows[key].update(write.values)
        return True


class DynamoStore:
    """Writes to the NimbusShared tables. `resource` is a boto3 dynamodb resource.

    Table names come from NIMBUS_TABLE_<TABLE> unless `table_names` is given.
    """

    def __init__(self, resource: Any = None, table_names: dict[str, str] | None = None) -> None:
        self._resource = resource
        self._names = table_names

    @property
    def resource(self) -> Any:
        if self._resource is None:
            import boto3

            self._resource = boto3.resource("dynamodb")
        return self._resource

    def table(self, name: str) -> Any:
        if self._names is not None:
            return self.resource.Table(self._names[name])
        return self.resource.Table(os.environ[TABLE_ENV_PREFIX + name.upper()])

    def apply(self, write: Write) -> bool:
        from boto3.dynamodb.conditions import Attr
        from botocore.exceptions import ClientError

        table = self.table(write.table)
        try:
            if isinstance(write, Put):
                if write.only_if_absent:
                    table.put_item(Item=write.item, ConditionExpression=Attr(KEYS[write.table][0]).not_exists())
                else:
                    table.put_item(Item=write.item)
                return True
            names = {f"#a{i}": k for i, k in enumerate(write.values)}
            values = {f":v{i}": v for i, v in enumerate(write.values.values())}
            table.update_item(
                Key=write.key,
                UpdateExpression="SET " + ", ".join(f"#a{i} = :v{i}" for i in range(len(names))),
                ExpressionAttributeNames=names,
                ExpressionAttributeValues=values,
                ConditionExpression=Attr(KEYS[write.table][0]).exists(),
            )
            return True
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                return False
            raise


def process(payload: dict[str, Any], store: Store) -> int:
    """Parse one EventBridge delivery and apply its writes. Returns how many were applied."""
    event = parse_eventbridge(payload)
    applied = 0
    for write in project(event):
        if store.apply(write):
            applied += 1
        else:
            log.info("skipped %s for %s %s: already applied or row missing", write.table, event.type, event.event_id)
    return applied


def _check_classified() -> None:
    types = {m.model_fields["type"].default for m in EVENT_TYPES}
    if types != PROJECTED | NOT_PROJECTED:
        raise RuntimeError(f"unclassified event types: {sorted(types ^ (PROJECTED | NOT_PROJECTED))}")


_check_classified()
