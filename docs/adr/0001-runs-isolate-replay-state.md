# Every piece of mutable state belongs to a Run

Storm Replay runs the same code as live mode, but Readings nudge Flood Thresholds and Trust Scores. Simulated Reports would therefore permanently skew live Velachery thresholds, and each repeat Replay would compound the nudges. So every mutable record (Readings, threshold nudges, Trust Scores, ledger entries, Work Orders, alerts) is keyed by a Run ID (`live` or a named Replay). Each Run starts from the Baseline Thresholds, and a Replay never reads or writes `live` state.

## Consequences

- Run ID is part of the partition key of every mutable DynamoDB table and part of every event on the bus, so it has to be fixed before the lanes start building.
- Hit rate is measured on a Prior-only Run so the team's simulated Reports can't inflate it.
