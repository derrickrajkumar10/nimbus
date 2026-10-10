# Nimbus

Street-level flood prediction and response for Chennai (hackathon build). The spec is `NIMBUS-Design-Lock.pdf`. Where it disagrees with `docs/adr/`, the ADRs win.

## Before writing code

- Use the terms in `CONTEXT.md`, in code as well as prose.
- Read `contracts/README.md`. Shared shapes live in `contracts/`. Never redefine an entity or event locally; import or generate it. Contract changes go through `contracts/generate.sh`.
- Every record and event carries `run_id`. Domain logic uses `sim_time`, never the wall clock.

## Layout

`contracts/` shared models and fixtures · `engines/` deterministic code · `agents/` Strands agents · `replay/` Storm Replay · `infra/` CDK (us-east-1) · `console/` React ward console · `app/` Flutter citizen app

## Agent skills

### Issue tracker

Issues are tracked in this repo's GitHub Issues via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Uses the five default triage labels (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
