# agents

Strands agents on Amazon Nova (ADR 0004). Specialists run as Lambdas triggered by EventBridge rules. The Commander runs on AgentCore Runtime. **Owner: Vishwa**, including the Verifier's F3 vision prompt.

Every outward action goes through a Cedar check (`cedarpy`), and every decision is emitted as `policy.decided`. Model IDs live in one per-agent config.
