# infra

AWS CDK in Python, region **us-east-1**. One CDK app, one stack file per lane, so lanes don't edit the same file. **Owner: Varun**, who owns the CDK app and `NimbusShared` (bus, tables from `contracts/storage.md`, buckets). Each lane fills in its own stack file: `NimbusEngines` (Goutam), `NimbusAgents` (Vishwa), `NimbusApi` and `NimbusConsole` (Varun).

| Stack | File | Owner |
|---|---|---|
| `NimbusShared` | `stacks/shared.py` | Varun |
| `NimbusEngines` | `stacks/engines.py` | Goutam |
| `NimbusAgents` | `stacks/agents.py` | Vishwa |
| `NimbusApi` | `stacks/api.py` | Varun |
| `NimbusConsole` | `stacks/console.py` | Varun |

## Finding the shared resources

Never hard-code a name. Read it from SSM (your Lambda role needs `ssm:GetParameter` on `/nimbus/*`):

| Parameter | Value |
|---|---|
| `/nimbus/bus/name`, `/nimbus/bus/arn` | the EventBridge bus (`nimbus`). Set `NIMBUS_EVENT_BUS` from the name |
| `/nimbus/tables/<Table>` | one per row of `contracts/storage.md`, e.g. `/nimbus/tables/SegmentRisk` |
| `/nimbus/buckets/photos` | Report and SOS photos, `reports/{run_id}/{report_id}.jpg` |
| `/nimbus/buckets/data` | F1 output, `segments/v{n}/segments.geojson` |

In a stack, resolve one at deploy time with `ssm.StringParameter.value_for_string_parameter(self, "/nimbus/bus/name")`.

Table notes:

- Tables are on-demand, named `nimbus-<Table>`, every key attribute a string.
- A composite key such as `run_id#segment_id` is **one attribute with that literal name**, holding values like `live#27320162-0`.
- `Segments` and the `data` bucket are kept if the stack is deleted. The rest are not.
- Sort keys that hold times (`Ledger.sim_time`, `Activity.emitted_at#event_id`) sort as text, so write them all in UTC at a fixed width, `%Y-%m-%dT%H:%M:%S.%fZ`, never with a `+05:30` offset and never the event's JSON string (it drops a zero fraction, so `07:00:00Z` would sort after `07:00:00.500000Z`).
- The bus archives every `nimbus.*` event for 7 days, for debugging.

## Deploy

One-off, per account (issue #1): `cdk bootstrap aws://<account>/us-east-1`.

```bash
cd infra
uv sync                      # Python 3.12 and dependencies
uv run pytest -q             # NimbusShared matches contracts/storage.md
cdk synth NimbusShared       # build the template, no AWS changes
cdk diff NimbusShared        # what would change
cdk deploy NimbusShared      # deploy one stack; deploy only your own lane's stack
```

Deploy your own lane's stack by name. Never `cdk deploy --all`.

## NimbusApi

Holds the event projector (`api/projector/`): one Lambda and one EventBridge rule on the shared bus, with a dead-letter queue. It may write only `Activity`, `Proposals`, `Alerts`, `Hazards`, `Readings` and `Sos`. `tests/test_api.py` fails if its role can touch any other table.

- **Bundling needs Docker or Podman** at `cdk synth`/`deploy`, to build the Lambda for Linux. The tests skip it (`aws:cdk:bundling-stacks: []`), so `pytest` doesn't need a container runtime.
- It reads the shared stack's tables directly, so deploy `NimbusShared` first.
- A deploy needs `cdk bootstrap` to have been run for the account (issue #1).

## Changing a table

Edit `TABLES` in `stacks/shared.py` **and** `contracts/storage.md` in the same PR. `tests/test_shared.py` fails if they disagree. Changing a key of a deployed table replaces it, because DynamoDB keys can't be altered in place, so ask in the team chat first.
