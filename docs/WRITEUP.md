# NIMBUS: street-level flood warnings for Chennai

Track: Heat and Water.

## The problem

In December 2023, Cyclone Michaung flooded Velachery, Chennai. City-wide warnings ("heavy rain expected") don't tell people which street will flood, or when to move a two-wheeler or a family. Ward officers had the same problem in reverse: no ranked picture of which streets needed pumps first.

## What we built

NIMBUS predicts flooding **per street segment**, warns the people who live there in **English and Tamil**, and proposes **which pump goes where**. An officer approves every large action. AI proposes; a human decides.

We replay the real Michaung storm (archived Open-Meteo rain, 2–5 Dec 2023) through the deployed system:

1. **Sentinel agent:** every 15 storm-minutes it scores 21 Velachery street segments with a deterministic risk engine (rain over the last 72 h plus the next 3 h, against each segment's flood threshold). It emits a `risk.changed` event when a street crosses `watch` → `likely`.
2. **Herald agent:** alerts the subscribers whose saved places are on that street, in English and Tamil, from fixed templates. Public safety text never contains invented facts. A street counts as safer only if all of it is low risk. A **Cedar** policy holds any alert to more than 100 people as a Ward Alert Proposal until an officer approves it.
3. **Dispatcher agent:** a greedy dispatch solver ranks free pumps against at-risk streets by impact (buildings nearby, confirmed readings, SOS) over travel time. The Dispatcher proposes each pick as a Work Order, with the numbers behind it. Cedar allows a crew to move only after an officer approves.
4. **Console API:** the ward console reads the live activity feed, risk and proposals. An officer approves or rejects a proposal with one call. Approval moves the pump `en_route` and is recorded on the event bus.

On the replay, the first street reaches `watch` at 2 Dec 17:45, about 34 hours before the first `likely` (4 Dec 03:45). All 21 segments reach `likely` by 07:45 on 4 Dec. `replay/HIT_RATE.md` has the per-street lead times and the method's limits.

## Where AWS fits

| Need | AWS service |
|---|---|
| Agents run on events, cost nothing when idle | **AWS Lambda** (Python 3.12): Sentinel, Herald, Dispatcher, projector, console API, citizen API, push sender |
| Agents talk only through events; a storm can be replayed | **Amazon EventBridge**: custom bus `nimbus`, a rule per agent and event type, a 7-day archive |
| State: risk per street, proposals, activity feed, pumps, subscribers | **Amazon DynamoDB**, on demand, every row keyed by `run_id` so replays never mix with live data |
| Ward console and citizen app backends | **Amazon API Gateway** HTTP APIs, throttled |
| Photos, config | **Amazon S3**, **SSM Parameter Store** |
| Everything as code | **AWS CDK** (Python): `NimbusShared`, `NimbusApi`, `NimbusAgents` |
| Guardrails | **Cedar** (AWS's open-source policy language) checks every outward agent action, and every decision is logged as `policy.decided` |
| Agent framework | **Strands Agents** (AWS open source), with Amazon Nova model settings per agent |

Build It: Strands Agents and Cedar. Ship It: deployed on Lambda, EventBridge, DynamoDB, API Gateway and S3 with CDK, in `us-east-1`.

**Honest note on models:** the agents are built with Strands and configured for Amazon Nova (Nova Lite for the Sentinel's plain-language reasons, Nova Pro for planning). Our AWS account is on the Free plan, where Bedrock model calls are not authorised, so this deployment runs the agents in rule and template mode. The Nova path is implemented and tested against a stubbed Bedrock.

## What's next

Real terrain thresholds from the Copernicus DEM on AWS Open Data (#13); Amazon Location for the map and safe two-wheeler routes (#15, #23); push alerts through FCM (sender built, needs Firebase credentials); a Commander agent officers can question; Cognito logins.

## AI tools used

See `docs/AI_TOOLS.md`.
