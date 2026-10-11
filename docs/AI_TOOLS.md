# AI tools used

- **Claude Code** (Anthropic): used by team members for writing and reviewing code, tests and documentation, for CDK infrastructure, and for debugging deployments. Every change went through a pull request, and its tests ran before merge.

Inside the product:

- **Strands Agents** (AWS open source): the agent framework for the Sentinel, Herald and Dispatcher.
- **Amazon Nova** (via Amazon Bedrock): the configured models (Lite and Pro). Not called in this deployment, because Bedrock isn't available on our account's Free plan; see `docs/WRITEUP.md`.
- Deterministic code, not AI, does the safety-critical parts: the risk score, the dispatch ranking and the alert wording.
