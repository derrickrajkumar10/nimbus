"""Load contracts/fixtures/ into the NimbusShared tables, so the console and app have something to show.

The demo scene (4 Dec 2023, 02:00 IST): 21 Velachery Segments with risk, one flooded Segment with a
Reading and a Hazard, three Resources, a pending Work Order Proposal, and an elderly SOS.

    uv run python tools/load_fixtures.py --dry-run                  # counts only, touches nothing
    uv run python tools/load_fixtures.py --run-id replay-michaung   # writes to AWS

Rows are validated against the contract models first, so a stale fixture fails here, not in the
console. Writing is idempotent: a row is replaced by the same row. Nothing is ever deleted.
`live` is refused unless --allow-live, because fixture risk shown to real users would be false.
"""

import argparse
import json
import re
import sys
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

from nimbus_contracts.entities import Hazard, Proposal, Reading, Resource, Segment, SegmentRisk, Sos
from pydantic import BaseModel, TypeAdapter

FIXTURES = Path(__file__).resolve().parents[2] / "contracts" / "fixtures"
TABLE_PREFIX = "nimbus-"  # NimbusShared names its tables nimbus-<Table> (infra/stacks/shared.py)
RUN_ID = re.compile(r"^(live|replay-[a-z0-9-]+)$")

# Table -> (fixture file, model, sort-key-free? i.e. whether rows carry run_id)
SOURCES: dict[str, tuple[str, type[BaseModel], bool]] = {
    "Segments": ("segments.json", Segment, False),  # static, no run_id
    "SegmentRisk": ("risk.json", SegmentRisk, True),
    "Readings": ("readings.json", Reading, True),
    "Hazards": ("hazards.json", Hazard, True),
    "Resources": ("resources.json", Resource, True),
    "Proposals": ("proposals.json", Proposal, True),
    "Sos": ("sos.json", Sos, True),
}


def rows_for(run_id: str, fixtures: Path = FIXTURES) -> dict[str, list[dict[str, Any]]]:
    """Every fixture row for `run_id`, as DynamoDB-ready dicts (floats are Decimal)."""
    if not RUN_ID.match(run_id):
        raise ValueError(f"run_id must be 'live' or 'replay-<name>', got {run_id!r}")
    out: dict[str, list[dict[str, Any]]] = {}
    for table, (name, model, per_run) in SOURCES.items():
        raw = json.loads((fixtures / name).read_text(encoding="utf-8"))
        if per_run:
            raw = [row | {"run_id": run_id} for row in raw]
        models = TypeAdapter(list[model]).validate_python(raw)
        out[table] = [json.loads(m.model_dump_json(), parse_float=Decimal) for m in models]
    return out


class MissingTable(RuntimeError):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.name = name


def load(resource: Any, rows: dict[str, list[dict[str, Any]]], prefix: str = TABLE_PREFIX) -> dict[str, int]:
    """Write `rows` through a boto3 dynamodb resource. Returns how many rows went to each table.

    Raises MissingTable when a table doesn't exist, which means NimbusShared isn't deployed there.
    """
    from botocore.exceptions import ClientError

    written = {}
    for table, items in rows.items():
        try:
            with resource.Table(prefix + table).batch_writer() as batch:
                for item in items:
                    batch.put_item(Item=item)
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") == "ResourceNotFoundException":
                raise MissingTable(prefix + table) from error
            raise
        written[table] = len(items)
    return written


def main(argv: Sequence[str] | None = None, resource: Any = None) -> int:
    parser = argparse.ArgumentParser(description="Load contracts/fixtures/ into the NimbusShared tables.")
    parser.add_argument("--run-id", default="replay-michaung", help="Run to load the scene into (default replay-michaung)")
    parser.add_argument("--prefix", default=TABLE_PREFIX, help=f"table name prefix (default {TABLE_PREFIX})")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--dry-run", action="store_true", help="validate and count rows, write nothing")
    parser.add_argument("--allow-live", action="store_true", help="allow loading into the live Run (don't)")
    args = parser.parse_args(argv)

    if args.run_id == "live" and not args.allow_live and not args.dry_run:
        parser.error("refusing to load fixture data into the live Run; pass --allow-live if you really mean it")
    try:
        rows = rows_for(args.run_id)
    except ValueError as error:
        parser.error(str(error))

    if args.dry_run:
        for table, items in rows.items():
            print(f"{args.prefix}{table}: {len(items)} rows (dry run)")
        return 0

    import boto3

    resource = resource or boto3.resource("dynamodb", region_name=args.region)
    try:
        written = load(resource, rows, args.prefix)
    except MissingTable as missing:
        print(
            f"{missing.name} doesn't exist in {_where(args.region)}. Deploy NimbusShared there first "
            "(infra/README.md), or point AWS_PROFILE at the account that has it. Nothing was written.",
            file=sys.stderr,
        )
        return 1
    for table, count in written.items():
        print(f"{args.prefix}{table}: wrote {count} rows to run {args.run_id if table != 'Segments' else '(static)'}")
    return 0


def _where(region: str) -> str:
    """'account 1234, us-east-1' for the credentials in use, so the message says where it looked."""
    try:
        import boto3

        return f"account {boto3.client('sts', region_name=region).get_caller_identity()['Account']}, {region}"
    except Exception:  # no credentials, no network: still say the region
        return f"the account your credentials point to, {region}"


if __name__ == "__main__":
    sys.exit(main())
