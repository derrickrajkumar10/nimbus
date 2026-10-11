# Ward console design

The ward console is the screen a Velachery ward officer works from during a storm. The agents rank what needs doing, and the officer approves it, watches the agents work, and asks the Commander questions. This document covers issues #11, #20 and the SOS and Ask the Commander parts of #27, built as one screen on fixture data, with a one-setting switch to the real API.

The approved visual reference is [`mockups/deep-tide-v2.html`](mockups/deep-tide-v2.html). Open it in a browser. It is interactive and uses the real fixtures. Where this document and the mockup disagree, this document wins.

## Why

- **The officer** needs one screen that says what to decide now and why, without hunting. Every Proposal is one click to approve.
- **The video and the judges** need the multi-agent story to be visible: agents acting in the feed, Cedar holding a Ward Alert, the officer approving, the Replay driving it all.
- **The team** needs the console working before the backend is finished, so it runs entirely on `contracts/fixtures/` and switches to Varun's API with one setting.

## Goals

1. The full screen from the mockup works on fixture data: top bar, Decisions, SOS, Resources, map, Replay timeline, Activity feed, Ask the Commander.
2. Setting one environment variable switches every read and write to the console HTTP API (`api/README.md`, merged in #45). No component changes.
3. It looks and behaves like production software. Clean, quiet, legible at 1080p in the video.
4. Few features, none of them dead ends. Everything on the map and in the lists can be clicked to inspect it. Every Proposal can be approved, edited or rejected.

## Non-goals (this build)

- Hit Rate panel and after-action report (rest of #27). Their API routes do not exist yet.
- Sign-in. Cognito is #19. The officer's name comes from config.
- A live Commander. The fixture Commander answers from fixture data. The real streaming endpoint (AgentCore, #29) plugs into the same interface later.
- Starting or pausing a real Replay. `GET/POST /runs` is not built. The controls are wired to an interface with a local implementation.
- WebSockets. Polling every 2 s is the workflow default.
- Phone and tablet layouts. The minimum width is 1280 px.
- Creating Resources, shelters or lake releases (officer input in the spec). Later.

## Anti-goals

These make the build a failure even if it works:

- **AI slop.** No gradients, glows, glassmorphism, emoji, avatar initial circles, sparkle icons, "AI-powered" labels, decorative illustrations or filler copy. Nothing on screen without a job.
- **Calling a predicted Segment "flooded".** Only a Reading makes a Segment flooded, and only that is drawn in water cyan.
- **Reading the wall clock for domain logic.** Times shown and computed (time to flood, SOS waiting time, the clock) come from `sim_time` and record timestamps. The wall clock is used for one thing only: "Updated N s ago", which measures the poll, not the storm.
- **Redefining contract shapes.** Types come from `contracts/generated/ts/nimbus.ts`.
- **Touching other lanes.** Only `console/` changes. Anything needed from another lane becomes an issue (listed at the end).

## Constraints

- **Stack (set by #11 and the spec):** Vite, React, TypeScript, MapLibre GL JS, OpenFreeMap tiles. Hosted on Amplify (Varun, #29).
- **Contracts:** import types from `contracts/generated/ts/nimbus.ts` and fixture JSON from `contracts/fixtures/` through a path alias. Never copy them into `console/`.
- **Runs:** every request carries `run_id`. The Run comes from the URL (`?run=replay-michaung`), defaulting to `replay-michaung`.
- **Terms:** use `CONTEXT.md` terms in code and copy: Segment, Proposal, Work Order, Ward Alert, Reading, Report, Hazard, Resource, SOS, Run, Replay, Risk Band.
- **Video:** the layout must hold at 1920×1080 and at 1280×800.
- **Isolation:** built in its own worktree on `derrick/11-console-shell`. The Flutter app work in the main checkout is untouched.

## Visual system

**Palette.** These are the citizen app's colours, so the phone and the console read as one product.

| Token | Value | Job |
|---|---|---|
| `--deep` | `#0A1F44` | page and top bar |
| `--panel` | `#0D2650` | docked panels, map controls, popups |
| `--raise` | `#12305E` | cards on panels |
| `--line` / `--line-2` | `rgba(169,198,219,.14)` / `.24` | hairline borders |
| `--text` / `--muted` / `--faint` | `#FFFFFF` / `#A9C6DB` / `#6F93B3` | text levels |
| `--teal` / `--teal-btn` | `#4FD1D9` / `#2FA9B8` | **only** officer actions, selection, "free" |
| `--watch` | `#F2B34A` | Risk Band watch; Cedar "Held" |
| `--likely` | `#FF7A57` | Risk Band likely; Hazards |
| `--water` | `#59D8E6` | **only** flooded (observed by a Reading) |
| `--low` | `#CFE3F0` at 45% opacity | Risk Band low |
| `--sos` | `#E8432A` | SOS only |

**Rules.**
- Each colour has one job. Nothing else gets colour. Agents are told apart by name, not by colour. This departs from #20's "one colour per agent" and was chosen with the mockup.
- Solid surfaces. No blur and no translucency except the map attribution.
- The only wave is the storm's rain curve in the Replay timeline, and it is data.
- **Type:** Outfit (300, 400, 500, 600), with Noto Sans Tamil for Tamil text. Both are bundled through `@fontsource`, never fetched at runtime. Numbers use `font-variant-numeric: tabular-nums`.
- **Icons:** a small set of custom inline SVGs (pump, crew, hazard, chevron, play and pause, check), 1.5 to 1.8 px strokes. No icon library.
- **Motion:** only where it carries meaning. The map flies to whatever is selected. The SOS marker has one slow ring pulse. Hover and press states are 150 ms colour changes. Respect `prefers-reduced-motion`.

**Basemap.** Load the OpenFreeMap `fiord` style and recolour it on load to the palette: background `#0B2347`, water `#06183A`, buildings `#133463`, roads `#21497D` with casings `#1B3F70`, labels `#7FA3C2` with a `#0B2347` halo. The mockup's `recolour()` function is the reference.

## Layout

A fixed grid, 56 px top bar, then three columns: left panel 384 px, map flexible, right panel 344 px. The Replay timeline (92 px) sits under the map only. Panels scroll on their own. The page never scrolls.

### Top bar

Left to right:
- the NIMBUS wordmark (same mark as the app) and the ward name;
- the Run switcher, a button showing the Run type ("Replay" tag in watch amber, "Live" in teal) and its name, which opens a menu of Runs. In fixture mode it lists `replay-michaung` only. In HTTP mode it lists the Runs in `VITE_RUNS` (default `replay-michaung,live`) until `GET /runs` exists. Switching sets `?run=` and reloads data. A `live` Run hides the Replay timeline, and its storm clock is still the newest time in the data. *(My call.)*;
- the storm clock: the newest `sim_time` in the loaded data, shown in IST as `02:00 Mon 4 Dec 2023`;
- the sync state: a teal dot and "Updated N s ago", turning amber with "Reconnecting…" after two failed polls;
- the officer's name.

### Left panel

Three sections, each with a header (title, count chip, a muted hint on the right).

**Decisions:** pending Proposals ordered by `rank`. The hint reads "Ranked by people affected".

Each card shows:
- the kind (Work Order or Ward Alert) and who proposed it at what time;
- a title built from the action. A Work Order reads "Send {Resource label} to {street name of the Segment}". A Ward Alert reads "Ward Alert to everyone in {Ward}". *(My call: `WardAlertDraft` has no Segment or ward, so the ward comes from config and the drafts carry the detail.)*;
- the Proposal's `reason`;
- for a Work Order, a facts row: buildings affected, the deepest linked Reading's depth, and the number of Reports behind those Readings;
- for a Ward Alert, the English and Tamil drafts with a "Held by Cedar" tag. Every Ward Alert is held, by definition in `CONTEXT.md`.

Behaviour:
- **Selecting.** Clicking a card selects it (teal border). A Work Order also flies the map to its Segment and opens its inspector. A Ward Alert has no Segment, so the map stays put. The first card is selected on load.
- **Approve** (primary button, key `A`) posts the decision. The card turns into a confirmation line in teal: "Approved by {officer} · {Resource} en route" for a Work Order, or "Approved by {officer} · Ward Alert sending" for a Ward Alert. The count drops, and an officer line appears at the top of the Activity feed.
- **Edit** (key `E`) opens an inline editor in the card. For a Work Order it is a choice among free Resources **of the same kind** (a pump Work Order can only take another pump). *(My call.)* For a Ward Alert it is the English and Tamil text. Saving posts `decision: "edited"` with the edited action.
- **Reject** (key `R`) asks inline, "Reject this Proposal?", with Reject and Cancel, then posts.
- **Decided Proposals** move into a collapsed "Decided (n)" row at the bottom of the section. It covers the whole Run, not only this session. *(My call: poll `/proposals` without a status filter and split pending from decided on the client. A Proposal decided by another officer moves to Decided and doesn't just vanish.)*
- **Errors.** A 409 replaces the buttons with "Already {status} by {who}". *(My call: config holds `VITE_OFFICER_ID`, sent as `decided_by`, and `VITE_OFFICER_NAME`, shown in the UI. When `decided_by` is this officer's ID, show the name. Otherwise show the raw ID until #19 brings real identities.)* A 502 retries once silently, then shows "Saved, but the alert didn't go out. Retry". Any other failure restores the buttons and shows a one-line error under them.
- **Empty state:** "Nothing needs you right now." in muted text.

**SOS:** SOS calls, ranked ones first. Each row shows the nearest Segment's street name, the people count, the flags (elderly, child, medical) in words, and the waiting time (storm clock minus `created_at`). Each row has an "Open" tag in SOS red. Clicking a row flies the map to it and opens its inspector.

**Resources:** label, the nearest Segment's street, and a status tag: Free in teal, En route as a teal outline, Working in muted grey. The hint reads "{free} of {total} free". Clicking a row flies the map to it.

### Map

- **Segments** are drawn as lines coloured by Risk Band, over a dark casing so they read against roads. Higher scores draw on top.
- **Readings** don't get their own pin. A flooded Segment shows the Reading in its inspector.
- **Hazards** are diamond pins in likely red, with a dashed no-go ring of `no_go_radius_m`.
- **Resources** are rounded-square pins with a pump or crew glyph: a teal border when free, grey when working, a dashed teal border when en route.
- **SOS** is a red circle showing the people count, with a slow ring pulse.
- **Labels** show on hover only, so a cluster stays readable.
- **Layer toggles**, top left: Risk, Readings, Hazards, Resources and SOS. Each hides its layer. Readings toggles the Reading section of the inspector and the cyan flooded colour back to its band colour.
- **Legend**, bottom left: Flooded, Likely, Watch and Low. **Zoom**, bottom right. Attribution is compact.
- **Initial camera:** fit to all Segments in the ward. On first load, select the first Decision and fly to its Segment.

**The inspector** is one popup design for everything clicked.
- **Segment:** street name, Segment ID, band tag, Risk Score, time to flood ("Now" when flooded, "—" when null) and Flood Threshold (mm). A flooded Segment also shows its Reading (depth, confidence, number of Reports). Then the numbered reasons.
- **Hazard:** class in words, owner, status, detected time and no-go radius.
- **Resource:** label, kind, status and nearest street.
- **SOS:** people, flags, waiting time and Triage rank and reasons when ranked.
- Only one inspector is open at a time. Esc closes it.

### Replay timeline

Shown only when the Run is a Replay.

- On the left: play and pause (key Space) and a speed button that cycles 15×, 30×, 60× and 120×.
- On the right: the storm's hourly rain as an area curve. The part before the storm clock is filled lighter. A white playhead sits at the storm clock with a label like "02:00 · 31 mm/h". The time axis is labelled at the start, at midnight, at 06:00 and at the end.
- The rain series is real Open-Meteo hourly precipitation for Velachery during Michaung (3 Dec 2023 18:00 to 4 Dec 12:00 IST). It lives in a console fixture file until the Replay lane serves it (see the issues at the end).
- In fixture mode, play, pause and speed change local state only. The data is one snapshot at 02:00, so the playhead and storm clock **stay at 02:00**. *(My call: the storm clock always reads from the data, so the screen is never inconsistent. With a real Replay running, the clock, the playhead, waiting times and time to flood all move as new `sim_time`s arrive. The filmed Replay runs on the deployed API at M3.)* The controls call a `ReplayControl` interface so the real `POST /runs` drops in later.

### Right panel

**Activity:** events from `/activity` (`agent.activity` and `policy.decided`), newest first.

- **Each row** shows the storm time (HH:MM), the agent's name and one sentence: `detail.decided` for agent activity. Clicking a row expands it to show `saw` and `why` in muted text.
- **Cedar rows:** a `policy.decided` with `allowed: false` shows "Cedar" with a "Held" tag and `detail.reason`. Allowed policy decisions are hidden by default, because they are noise.
- **Officer decisions** appear as officer rows in teal, built from decided Proposals (`decided_by`, `decided_at`, `status`) and merged into the feed by time. They survive a reload and include other officers' decisions. `proposal.decided` is not in the API feed.
- **Filter:** an "All agents" menu in the header narrows the feed to one agent, or to Cedar.
- **New rows** slide in at the top. If the officer has scrolled down, the feed holds its place and shows a "{n} new" pill instead.

**Ask the Commander:** an input pinned under the feed (key `/` focuses it).

- Submitting adds the question and the Commander's answer to the feed as one block in a slightly raised card. The answer streams in.
- In fixture mode the answer is assembled from the loaded data: what changed in the last hour (the activity), what's pending (the Decisions), and the top risk (the highest-scoring Segments). It streams word by word at a natural pace.
- The client is a `CommanderClient` interface with `ask(question, run_id): AsyncIterable<string>`, so the AgentCore stream replaces it without UI changes.
- One question at a time. The input is disabled while an answer streams.

## Data

**One interface, two sources.** Components read through `NimbusSource`:

- `segments()`, `risk()`, `readings()`, `hazards()`, `resources()`, `sos()`, `proposals(status?)`
- `activity(since?)` returns `{ items: Event[], cursor }`
- `decide(proposalId, decision)`
- `commander`: a `CommanderClient`
- `replay`: a `ReplayControl`

**Fixture source** (default). It reads `contracts/fixtures/*.json` and `segments.geojson`, plus a small console scene file for what the contracts have no fixtures for yet:
- the activity events (typed as the contract `Event`), matching the mockup's feed;
- the Herald's Ward Alert Proposal (typed as `Proposal`);
- the rain series.

Decisions are kept in memory and behave like the API, including 409 on a repeat decision by someone else.

**HTTP source.** It is selected when `VITE_NIMBUS_API` is set to the console API base URL. Requests follow `api/README.md` exactly:
- `run_id` on every route;
- `/proposals?status=pending`;
- `/activity` with the cursor;
- `POST /proposals/{id}/decision` with `{run_id, decision, decided_by, action?}`.

The request body has no generated type yet (it lives in `api/console/routes.py`). Build it from contract types (`Proposal["action"]`, `ProposalStatus`) and file an issue to move `DecisionRequest` into `contracts/`. Segments come from the citizen API's existing `GET /segments` (`Segment[]`, static) at `VITE_CITIZEN_API`, converted to GeoJSON in the console and loaded once. Without that variable, they come from the fixture GeoJSON. *(My call.)*

**Polling.** One 2 s heartbeat refreshes proposals, activity, risk, resources and SOS. Hazards and readings refresh every 10 s, and segments load once. Use TanStack Query: `refetchInterval` for polling, mutations with optimistic updates for decisions, and a rollback on error. "Updated N s ago" is the time since the last successful heartbeat.

**Derived values** live in plain functions with unit tests, not in components:
- proposal titles;
- the nearest Segment's street for a point;
- waiting minutes;
- the storm clock (the max `sim_time`);
- band to colour;
- the depth and Report counts for a Work Order;
- the fixture Commander's answer.

## Quality bar

- **TypeScript** strict, with ESLint (the Vite React config). `npm run build` and `npm run typecheck` must pass.
- **Tests** use Vitest and React Testing Library. They cover:
  - the derived-value functions;
  - the fixture source, including decisions and 409s;
  - the HTTP source's request shapes, with `fetch` mocked;
  - the Decision card flows (approve, edit, reject, the error states);
  - keyboard shortcuts;
  - the feed's Cedar and officer rows.

  MapLibre is mocked in unit tests.
- **Visual check:** a headless screenshot at 1920×1080 and 1280×800 compared against the mockup before calling it done.
- **Accessibility:** every button is a real `<button>` with a label, and focus rings are visible (2 px teal outline). Text meets 4.5:1 contrast on its surface. Keyboard shortcuts never fire while typing in an input.

## Left to the builder

- **Code structure:** folder layout inside `console/src/`, component boundaries, and CSS approach (CSS Modules plus one `tokens.css` is the suggestion; no Tailwind, so the tokens stay explicit).
- **Map code:** exact MapLibre layer IDs, and whether pins are HTML markers or symbol layers. Markers are fine at fixture scale. Symbol layers are better if F1 brings thousands of Segments.
- **Copy:** the exact wording of the fixture Commander's answer, within the facts in the fixtures.
- **Small layout details:** spacing and sizes, where the mockup is silent.

## Issues to open for other lanes

1. **Contracts** (team-chat heads-up): fixtures for `agent.activity` and `policy.decided` events and a Ward Alert Proposal, so the console scene can move out of `console/`. Move `DecisionRequest` into `contracts/`. Add optional `segment_ids` to `WardAlertDraft`, so a Ward Alert can show and fly to the road it is about.
2. **API, Varun:** CORS on both the console and citizen HTTP APIs must allow the console's Amplify origin and `http://localhost:5173`. Confirm that the Amplify build clones the whole repo (app root `console/`), because the console imports `../contracts`.
3. **Replay, Goutam, and API, Varun:** serve the Run's rain series and its start and end with `GET /runs`, so the timeline stops using the console fixture.
4. **CI, Varun:** a console job that runs typecheck, lint, test and build on changes under `console/`.
5. **Commander, Vishwa, and Deploy, Varun:** the streaming endpoint and its message format for Ask the Commander.
