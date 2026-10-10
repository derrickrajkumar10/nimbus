# Team workflow

Four people, four Claude Code sessions, one `main` branch, and a feature freeze at **Sun 12:00**. This page covers who owns what, how code reaches `main`, and when the pieces meet.

## Who owns what

| Who | Lane | Owns these folders | Builds |
|---|---|---|---|
| **Goutam** | Data and engines | `engines/`, `replay/` | F1 sink map, F2 risk engine, F6 router, dispatch solver, F9 Replay and Hit Rate |
| **Vishwa** | Agents and policy | `agents/` | All 8 Strands agents on Nova, F3 vision prompt (Verifier), Cedar policies, EventBridge rules |
| **Derrick** | Front ends | `console/`, `app/` | React ward console, Flutter citizen app, video lead on Sunday |
| **Varun** | Integration | `infra/`, `api/`, `.github/` | AWS account, CDK shared stack, HTTP API, auth, FCM sender, deploys, CI, **reviews and merges every PR** |

`contracts/` is shared. Changing it requires a heads-up in the team chat and Varun's review (see below).

**Stay in your folders.** If you need something from another lane, open an issue for that lane and keep building against `contracts/fixtures/`. Tell your Claude Code the same thing.

## How work reaches main

1. **Pick an issue** from your lane on the [issue board](https://github.com/derrickrajkumar10/nimbus/issues). Each issue has an `owner:` label and a checkpoint milestone.
2. **Branch** `<your-name>/<issue#>-<slug>`, for example `goutam/3-risk-engine`.
3. **Start your Claude Code session** with:
   > Read CLAUDE.md, CONTEXT.md and contracts/README.md, then work on issue #N (`gh issue view N`). Only edit files in `<your folders>`.
4. **Open a small PR early** with `Closes #N` in the body. Push often: a PR that's two hours old is a merge conflict waiting to happen.
5. **CI runs** the contract tests and checks that generated files are current.
6. **Varun squash-merges** once CI is green. While Varun is asleep, authors merge their own PRs once CI is green.
7. **Pull `main` at least every hour.** Run `git pull --rebase origin main` before pushing.

### Changing a contract

Contract changes ripple into three languages, so:

1. Post in the team chat: what's changing and why.
2. Edit the model in `contracts/src/`, run `contracts/generate.sh`, and commit the regenerated files in the **same PR**.
3. Varun reviews and merges it ahead of other PRs, and tells everyone to pull.

Prefer adding optional fields over renaming or removing them.

## Checkpoints

Each checkpoint is a GitHub milestone. Varun runs the end-to-end check at every checkpoint and files bugs as issues.

| When | Milestone | Done means |
|---|---|---|
| **Sat 23:15** | M0 Setup | Everyone has AWS access (us-east-1), Nova enabled in Bedrock, Firebase project made, the shared stack deployed, CI green |
| **Sun 02:00** | M1 Walking skeleton | On fixture data, a `clock.tick` produces `risk.changed`, the Herald pushes a Tamil alert to a real phone, the console shows the map and a Proposal, and the app shows the map and a Saved Place |
| **Sun 07:00** | M2 Real engines | Real F1 Segments for Velachery, a Michaung Replay running on the Replay Driver, a photo turning into a Reading, the router detouring, the Dispatcher proposing Work Orders |
| **Sun 10:30** | M3 Demo path | Every beat of the video works on the deployed app: Commander conflict, Cedar holding a Ward Alert, SOS card, Hit Rate, after-action report |
| **Sun 12:00** | **Freeze** | Nothing new starts. Bug fixes only. |
| Sun 12:00–16:00 | Film and submit | Derrick leads the recording, Varun keeps the deploy stable, Goutam and Vishwa write the blog |

### Sleep in shifts

- **Shift A, Goutam and Derrick:** sleep **02:15–05:30**, right after M1.
- **Shift B, Vishwa and Varun:** sleep **05:30–09:00**. Before sleeping, Varun starts a full Michaung Replay and leaves its log for Shift A to read.

Swap if that suits someone better. Just keep one person from each pair awake.

## AWS

- **One account, region us-east-1** (ADR 0004). Each person gets their own IAM user. Nobody uses the root account.
- **CDK stacks per lane** so deploys don't collide:
  - `NimbusShared` (Varun): bus, tables and buckets
  - `NimbusEngines` (Goutam)
  - `NimbusAgents` (Vishwa)
  - `NimbusApi` (Varun)
  - `NimbusConsole` (Varun, hosting Derrick's build)
- **Budget alarm at $25.** Keep Bedrock calls cached per photo.
- **Secrets** (Firebase service account and similar) go in AWS Secrets Manager, never in git.

## Open decisions

The person who hits one of these first asks Derrick and records the answer in `CONTEXT.md` or an ADR:

- Whether an officer's edit to a Proposal re-runs the Cedar check (Vishwa, Derrick)
- How far the Commander can re-rank on its own before asking an officer (Vishwa)
- When a flooded Segment goes back to normal after the last Reading (Goutam)
- What signals the end of a storm for the Chronicler (Goutam, Vishwa)
- How far one Reading moves a Flood Threshold (Goutam)
- Whether the console gets live updates by polling every 2 s (default) or over a WebSocket (Varun, Derrick)
