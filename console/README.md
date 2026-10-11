# console

Ward console: React + MapLibre GL JS on Amplify Hosting. **Owner: Derrick.** Types come from `contracts/generated/ts/nimbus.ts`. It runs on `contracts/fixtures/` until `VITE_NIMBUS_API` points at the console API.

The design and its reasons are in [docs/design.md](docs/design.md). The approved mockup is [docs/mockups/deep-tide-v2.html](docs/mockups/deep-tide-v2.html).

![The console on the fixture scene at 1920×1080](docs/screenshots/console-1080.png)

## Run it

```bash
npm install
npm run dev          # http://localhost:5173, fixture data
```

Checks (CI should run all four):

```bash
npm test             # Vitest
npm run typecheck
npm run lint         # oxlint
npm run build        # also bundles the MapLibre worker
```

## Settings

Copy `.env.example` to `.env.local`. With nothing set, the console runs on fixtures.

| Variable | What it does |
|---|---|
| `VITE_NIMBUS_API` | Console API base URL (`ConsoleApiUrl`). Set it to switch every read and decision to the API. |
| `VITE_CITIZEN_API` | Citizen API base URL, used only for `GET /segments`. Without it, Segments come from the fixture. |
| `VITE_OFFICER_ID` | Sent as `decided_by` until Cognito (#19). Default `officer-1`. |
| `VITE_OFFICER_NAME` | Shown in the UI. Default `K. Priya`. |
| `VITE_WARD_NAME` | Default `Velachery`. |
| `VITE_RUNS` | Runs in the switcher until `GET /runs` exists. Default `replay-michaung,live`. |

The Run comes from the URL: `?run=replay-michaung` (default) or `?run=live`.

## Keyboard

| Key | Does |
|---|---|
| `A` / `E` / `R` | Approve, edit or reject the selected Decision |
| `/` | Ask the Commander |
| `Space` | Play or pause the Replay |
| `Esc` | Close the map inspector |

Shortcuts never fire while you're typing.

## Still on fixtures

These have no backend yet, so the console fills them itself (see design.md, "Issues to open for other lanes"):

- the agent feed events and the Herald's Ward Alert (`src/data/fixtureScene.ts`);
- the storm's rain curve (real Open-Meteo values for Velachery);
- Replay play, pause and speed (local only until `POST /runs`);
- the Commander's answers, built from the loaded data until the AgentCore endpoint exists.
