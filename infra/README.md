# infra

AWS CDK in Python, region **us-east-1**. One CDK app, one stack file per lane, so lanes don't edit the same file. **Lane 4** owns the app and the shared stack (bus, tables from `contracts/storage.md`, buckets).
