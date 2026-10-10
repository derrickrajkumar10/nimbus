# infra

AWS CDK in Python, region **us-east-1**. One CDK app, one stack file per lane, so lanes don't edit the same file. **Owner: Varun**, who owns the CDK app and `NimbusShared` (bus, tables from `contracts/storage.md`, buckets). Each lane fills in its own stack file: `NimbusEngines` (Goutam), `NimbusAgents` (Vishwa), `NimbusApi` and `NimbusConsole` (Varun).
