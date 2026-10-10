# agents

Strands agents on Amazon Nova (ADR 0004). Specialists run as Lambdas triggered by EventBridge rules. The Commander runs on AgentCore Runtime. **Lane 2 (agents and policy).** The Verifier's vision prompt is **Lane 4**.

Every outward action goes through a Cedar check (`cedarpy`), and every decision is emitted as `policy.decided`. Model IDs live in one per-agent config.
