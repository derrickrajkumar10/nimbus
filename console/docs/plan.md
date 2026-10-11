# Ward Console Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the full Deep tide ward console (Decisions, SOS, Resources, map, Replay timeline, Activity, Ask the Commander) on fixture data, switching to the console HTTP API with one environment variable.

**Architecture:** A Vite + React + TypeScript single page in `console/`. Components read data through one `NimbusSource` interface with a fixture source and an HTTP source. TanStack Query runs a 2 s heartbeat. Pure functions in `src/domain/` hold every derived value. MapLibre draws the map on a recoloured OpenFreeMap `fiord` style.

**Tech Stack:** Vite (`npm create vite@latest`, react-ts template; keep the versions the template pins), React, TypeScript (strict), MapLibre GL JS, @tanstack/react-query 5, Vitest, React Testing Library, jsdom, @fontsource/outfit and @fontsource/noto-sans-tamil, CSS Modules.

**Spec:** `console/docs/design.md`. The visual reference is `console/docs/mockups/deep-tide-v2.html`. Read both before any task.

## Global Constraints

- Work only in `console/` on branch `derrick/11-console-shell` (worktree `.claude/worktrees/derrick+11-console-shell`). Never edit `contracts/`, `api/`, `app/` or anything else.
- Types come from `@contracts/generated/ts/nimbus` (alias for `../contracts`). Fixture data comes from `@contracts/fixtures/*.json`. Never copy or redefine them. The Resource entity is generated as `Resource1`: `import type { Resource1 as Resource }`.
- Every source call takes `runId`. The default Run is `replay-michaung`, read from `?run=`.
- Domain times come from `sim_time` and record timestamps, never `Date.now()`. The only wall-clock use is "Updated N s ago".
- Use the `CONTEXT.md` terms in code and copy: Segment, Proposal, Work Order, Ward Alert, Reading, Report, Hazard, Resource, SOS, Run, Replay, Risk Band. Never label a predicted Segment "Flooded".
- Colours come only from the tokens in design.md "Visual system". Teal is for officer actions, selection and "free". Cyan `#59D8E6` is only for flooded Segments.
- No gradients, glows, blur, emoji, avatar circles or icon libraries. Icons are inline SVG in `src/ui/icons.tsx`.
- Fonts are bundled through @fontsource. Nothing is fetched at runtime except map tiles and the style.
- Minimum width is 1280 px. The page never scrolls; panels scroll on their own. Check the layout at 1920×1080 and 1280×800.
- Keyboard: `A` approve, `E` edit, `R` reject (selected Decision), `/` focuses Ask the Commander, Space plays or pauses the Replay, Esc closes the inspector. Shortcuts never fire while focus is in an input or textarea.
- Commands, run from `console/`: `npm test` (vitest run), `npm run typecheck`, `npm run lint`, `npm run build`. All four pass at the end of every task.
- Commit after each task with a message in the repo's style (sentence case, no prefix). End every message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **A 409 on approve.** Someone else decided first, so the card shows "Already approved by officer-2" and does not stay optimistic. *(Task 7 test.)*
2. **Pressing `A` while typing a question for the Commander.** It must not approve anything. *(Task 6 shortcut test, and Task 10 integration test.)*
3. **A Run with no data** (empty arrays from every call, e.g. `?run=live` on fixtures). The page renders empty states, the storm clock shows "—" and nothing throws. *(Task 13 integration test.)*
4. **A poll that fails twice, then recovers.** The sync shows "Reconnecting…", then returns to "Updated 0 s ago" without a reload. *(Task 5 test.)*
5. **`minutes_to_flood: null` and a Segment without a `street_name`.** The inspector shows "—" for time to flood and "Unnamed road" for the street. *(Task 2 and Task 11 tests.)*

---

## File map

```
console/
  index.html, package.json, vite.config.ts, tsconfig*.json, eslint.config.js, .env.example
  src/
    main.tsx, App.tsx, App.module.css
    config.ts                      env + URL → Config
    styles/tokens.css, global.css
    domain/                        pure, unit-tested
      bands.ts  time.ts  geo.ts  proposals.ts  sos.ts  activity.ts  rain.ts  commander.ts
    data/
      source.ts                    NimbusSource interface + shared data types
      fixtureScene.ts              console-only fixture data (events, Ward Alert, rain)
      fixtureSource.ts  httpSource.ts  createSource.ts
      queries.tsx                  SourceProvider, useConsoleData, useDecide, useSyncStatus
    state/
      selection.tsx                selected Decision + inspected map target
      shortcuts.ts                 useShortcuts
    ui/
      icons.tsx  TopBar.tsx  RunSwitcher.tsx
      DecisionsPanel.tsx  DecisionCard.tsx  DecisionEditor.tsx
      SosSection.tsx  ResourcesSection.tsx
      ActivityPanel.tsx  FeedRow.tsx  AskCommander.tsx
      map/MapView.tsx  map/basemap.ts  map/layers.ts  map/Inspector.tsx  map/MapOverlays.tsx
      ReplayBar.tsx  RainChart.tsx
      *.module.css next to each component
    test/setup.ts  test/maplibre.ts  test/fakeSource.ts
```

---

### Task 1: Scaffold the console

**Files:**
- Create: everything under `console/` listed at the top of the file map, plus `src/styles/*`, `src/test/setup.ts` and `src/smoke.test.ts`
- Keep: `console/README.md`, `console/docs/`

**Interfaces:**
- Produces: alias `@contracts/*` → `../contracts/*` in both `vite.config.ts` (`resolve.alias`, `server.fs.allow: ['..']`) and `tsconfig.app.json` (`paths`), with `resolveJsonModule: true`. CSS custom properties from design.md "Visual system" in `src/styles/tokens.css`. Scripts `test`, `typecheck`, `lint`, `build`, `dev`.

- [ ] **Step 1: Scaffold.** Run `npm create vite@latest console-tmp -- --template react-ts` in the scratchpad. Move its files into `console/` without overwriting `README.md` or `docs/`. Delete the demo assets and the counter App. Run `npm install`.
- [ ] **Step 2: Add dependencies:** `npm i maplibre-gl @tanstack/react-query @fontsource/outfit @fontsource/noto-sans-tamil` and `npm i -D vitest jsdom @testing-library/react @testing-library/user-event @testing-library/jest-dom`.
- [ ] **Step 3: Configure.**
  - Add the alias described above.
  - In `vite.config.ts`, set `test: { environment: 'jsdom', setupFiles: './src/test/setup.ts', css: { modules: { classNameStrategy: 'non-scoped' } } }`.
  - `setup.ts` imports `@testing-library/jest-dom/vitest`.
  - Add the scripts `"test": "vitest run"` and `"typecheck": "tsc -b --noEmit"`.
  - `.env.example` lists `VITE_NIMBUS_API=`, `VITE_CITIZEN_API=`, `VITE_OFFICER_ID=officer-1`, `VITE_OFFICER_NAME=K. Priya`, `VITE_WARD_NAME=Velachery`, `VITE_RUNS=replay-michaung,live`.
- [ ] **Step 4: Write the smoke test** `src/smoke.test.ts`:

```ts
import risk from '@contracts/fixtures/risk.json';
import type { SegmentRisk } from '@contracts/generated/ts/nimbus';
test('contracts alias resolves fixtures and types', () => {
  const rows = risk as SegmentRisk[];
  expect(rows.find(r => r.segment_id === '27480309-1')?.band).toBe('flooded');
});
```

- [ ] **Step 5: Run the smoke test.** `npm test`. Expected: 1 passed.
- [ ] **Step 6: Add the styles.**
  - `tokens.css`: every token from design.md.
  - `global.css`: box-sizing; `html, body, #root { height: 100%; }`; body `background: var(--deep)`, Outfit, antialiased; `button` reset; `:focus-visible { outline: 2px solid var(--teal); outline-offset: 2px; }`; `.num { font-variant-numeric: tabular-nums; }`; `@media (prefers-reduced-motion: reduce)` that disables animations and transitions.
  - `main.tsx` imports `@fontsource/outfit/{300,400,500,600}.css`, `@fontsource/noto-sans-tamil/{400,500}.css`, `maplibre-gl/dist/maplibre-gl.css` and both style files. `App.tsx` renders `<div>Nimbus</div>` for now.
- [ ] **Step 7: Verify.** `npm run typecheck && npm run lint && npm run build`. All pass.
- [ ] **Step 8: Commit.** `Scaffold the ward console (#11)`

---

### Task 2: Domain functions

**Files:**
- Create: `src/domain/{bands,time,geo,proposals,sos}.ts` and a `*.test.ts` next to each

**Interfaces:**
- Consumes: contract types only.
- Produces:

```ts
// bands.ts
export const BAND_COLOR: Record<RiskBand, string>;   // flooded #59D8E6, likely #FF7A57, watch #F2B34A, low #CFE3F0
export const BAND_LABEL: Record<RiskBand, string>;   // Flooded, Likely, Watch, Low
// time.ts  (all display in Asia/Kolkata)
export function stormClock(times: string[]): string | null;         // latest ISO by instant, null if empty
export function formatClock(iso: string): { time: string; date: string }; // { time: '02:00', date: 'Mon 4 Dec 2023' }
export function hhmm(iso: string): string;                           // '01:55'
export function minutesBetween(fromIso: string, toIso: string): number; // floor, never negative
// geo.ts
export type SegmentProps = { segment_id: string; street: string; band: RiskBand; score: number };
export function streetName(s: Segment): string;                      // street_name ?? 'Unnamed road'
export function segmentsToGeoJSON(segments: Segment[], risk: SegmentRisk[]): GeoJSON.FeatureCollection<GeoJSON.LineString, SegmentProps>; // a Segment without risk → band 'low', score 0
export function nearestSegment(p: GeoPoint, segments: Segment[]): Segment | null; // min distance from point to any line piece, equirectangular metres
export function segmentMidpoint(s: Segment): [number, number];       // [lon, lat] of the middle vertex
export function circlePolygon(c: GeoPoint, radiusM: number, steps?: number): GeoJSON.Feature<GeoJSON.Polygon>;
// proposals.ts
export type ProposalContext = { resources: Resource[]; segments: Segment[]; readings: Reading[]; wardName: string };
export function proposalTitle(p: Proposal, ctx: ProposalContext): string;
export function workOrderFacts(wo: WorkOrder, readings: Reading[]): { buildings: number; depth: DepthBand | null; reports: number };
export function splitProposals(ps: Proposal[]): { pending: Proposal[]; decided: Proposal[] }; // pending by rank asc; decided by decided_at desc
export function isWorkOrder(a: Proposal['action']): a is WorkOrder;  // kind === 'work_order' or has resource_id
export function deciderName(decidedBy: string | null | undefined, officerId: string, officerName: string): string;
export function confirmationLine(p: Proposal, ctx: ProposalContext & { officerId: string; officerName: string }): string;
// sos.ts
export function sosFlagsText(f: VulnerabilityFlags): string;         // 'Elderly resident', 'Child', 'Medical need', joined ' · '; '' if none
export const HAZARD_LABEL: Record<HazardClass, string>;              // Open manhole, Live wire, Fallen tree, Stranded vehicle
export const OWNER_LABEL: Record<HazardOwner, string>;               // Corporation, Power utility
```

Exact copy:
- `proposalTitle`:
  - Work Order: `Send ${resource.label} to ${streetName(segment)}`.
  - Ward Alert: `Ward Alert to everyone in ${wardName}`.
- `confirmationLine`:
  - approved or edited Work Order: `Approved by ${name} · ${label} en route`.
  - approved or edited Ward Alert: `Approved by ${name} · Ward Alert sending`.
  - rejected: `Rejected by ${name}`.
  - Use "Edited and approved by" in place of "Approved by" when the status is `edited`.

- [ ] **Step 1: Write the failing tests.** Use the real fixtures (`@contracts/fixtures/*.json` cast to contract types). Each test name lists its assertions:
  - `stormClock returns the latest instant across offsets`: `['2023-12-04T02:00:00+05:30','2023-12-03T20:15:00Z']` → the first. `[]` → `null`.
  - `formatClock renders IST`: `'2023-12-03T20:30:00Z'` → `{ time: '02:00', date: 'Mon 4 Dec 2023' }`.
  - `minutesBetween floors and clamps`: sos created 01:55 to 02:00 → `5`. Reversed → `0`.
  - `segmentsToGeoJSON joins risk`: 21 features. `27480309-1` has band `flooded` and score `92`. A segment missing from risk gets `low`/`0`.
  - `streetName falls back`: `{...seg, street_name: null}` → `'Unnamed road'`.
  - `nearestSegment finds Velachery Main Road for Pump 2`: Pump 2's location → street `'Velachery Main Road'`. `[]` → `null`.
  - `circlePolygon closes the ring`: first coordinate equals last; 49 points for the default steps of 48.
  - `proposalTitle for the fixture Work Order`: `'Send Pump 2 to Velachery Main Road'`.
  - `proposalTitle for a Ward Alert`: `'Ward Alert to everyone in Velachery'`.
  - `workOrderFacts`: fixture pr-0001 → `{ buildings: 17, depth: 'knee', reports: 3 }`. No readings → `{ buildings: 17, depth: null, reports: 0 }`.
  - `splitProposals orders pending by rank and decided by decided_at desc`.
  - `deciderName`: own id → officer name. Another id → that id. `null` → `'another officer'`.
  - `confirmationLine` covers all three statuses for both kinds.
  - `sosFlagsText`: `{elderly:true,child:false,medical:true}` → `'Elderly resident · Medical need'`.
- [ ] **Step 2:** `npm test`. The new tests fail (modules missing).
- [ ] **Step 3: Implement** the signatures above. Use `Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Kolkata', … })` for times. Distance is equirectangular: `x = Δlon·cos(lat)·111320`, `y = Δlat·110540`, point-to-segment projection.
- [ ] **Step 4:** `npm test`. All pass. Then typecheck and lint.
- [ ] **Step 5: Commit.** `Add console domain functions`

---

### Task 3: Source interface, console fixture scene and fixture source

**Files:**
- Create: `src/data/source.ts`, `src/data/fixtureScene.ts`, `src/data/fixtureSource.ts`, `src/data/fixtureSource.test.ts`

**Interfaces:**
- Produces, in `source.ts`:

```ts
export type SosRow = Sos & Partial<Omit<RankedSos, 'sos_id'>>;
export type Decision = 'approved' | 'edited' | 'rejected';
export type DecisionInput = { decision: Decision; decided_by: string; action?: WorkOrder | WardAlertDraft };
export type DecisionErrorCode = 'already_decided' | 'proposal_not_found' | 'event_not_sent' | 'invalid' | 'network';
export class DecisionError extends Error {
  constructor(public code: DecisionErrorCode, message: string,
              public detail: { current_status?: ProposalStatus; decided_by?: string | null } = {}) { super(message); }
}
export type ActivityPage = { items: Event[]; cursor: string | null };
export type RainPoint = { time: string; mm: number };        // ISO with +05:30
export type ReplaySpeed = 15 | 30 | 60 | 120;
export type ReplayState = { playing: boolean; speed: ReplaySpeed };
export interface ReplayControl { get(runId: string): ReplayState; set(runId: string, next: ReplayState): Promise<ReplayState>; }
export interface CommanderClient { ask(question: string, runId: string): AsyncIterable<string>; }
export interface NimbusSource {
  readonly mode: 'fixtures' | 'http';
  runs(): string[];
  segments(): Promise<Segment[]>;
  risk(runId: string): Promise<SegmentRisk[]>;
  readings(runId: string): Promise<Reading[]>;
  hazards(runId: string): Promise<Hazard[]>;
  resources(runId: string): Promise<Resource[]>;
  sos(runId: string): Promise<SosRow[]>;
  proposals(runId: string): Promise<Proposal[]>;               // every status
  activity(runId: string, since?: string | null): Promise<ActivityPage>; // oldest first, cursor exclusive
  decide(runId: string, proposalId: string, input: DecisionInput): Promise<Proposal>;
  rain(runId: string): Promise<RainPoint[]>;
  readonly replay: ReplayControl;
  commander: CommanderClient;                                  // set by createSource (Task 10)
}
```

- Produces, in `fixtureScene.ts` (all `run_id: 'replay-michaung'`, `emitted_at` = `sim_time` converted to UTC with a `Z`, `source` = the agent name, `event_id` = `ev-000N`):
  - `SCENE_EVENTS: Event[]`, oldest first. The time is the `sim_time` on 4 Dec 2023 in +05:30. The "decided" column is `detail.decided`; write a short `saw` and `why` consistent with it.

    | sim time | type / agent | decided |
    |---|---|---|
    | 01:45 | agent.activity / pathfinder | Closed Velachery Main Road to cars and two-wheelers. |
    | 01:50 | agent.activity / verifier | Merged 3 Reports into a knee-deep Reading on Velachery Main Road. Confidence 0.82. |
    | 01:50 | agent.activity / verifier | Found an open manhole. Added a 30 m no-go zone and sent it to the corporation. |
    | 01:55 | agent.activity / triage | Ranked the Ram Nagar SOS first. 3 people, one elderly. |
    | 02:00 | agent.activity / sentinel | Velachery Main Road north moved to likely: 32 mm forecast in 3 h, ground saturated. |
    | 02:00 | agent.activity / dispatcher | Proposed Pump 2 for Velachery Main Road. It is the nearest free pump. |
    | 02:00 | policy.decided | principal `herald`, action `SendAlert`, resource `proposal:pr-0002`, allowed `false`, reason `Stopped the Herald's ward-wide alert until an officer approves it.` |
    | 02:00 | policy.decided | principal `dispatcher`, action `ProposeWorkOrder`, resource `proposal:pr-0001`, allowed `true`, reason `Dispatcher may propose Work Orders.` |

  - `SCENE_WARD_ALERT: Proposal`:
    - `proposal_id: 'pr-0002'`, `proposed_by: 'herald'`, `rank: 2`, `created_at: '2023-12-04T02:00:00+05:30'`, `status: 'pending'`, `decided_by: null`, `decided_at: null`;
    - `reason: 'The Herald drafted this for the whole ward. Ward-wide alerts wait for an officer.'`;
    - `action`: `{ kind: 'ward_alert', message_en: 'Velachery Main Road is flooded knee-deep. Use 100 Feet Road.', message_ta: 'வேளச்சேரி மெயின் ரோட்டில் முழங்கால் அளவு தண்ணீர். 100 அடி சாலையைப் பயன்படுத்தவும்.', recipient_count: 1240 }`.
  - `MICHAUNG_RAIN: RainPoint[]`: Open-Meteo hourly precipitation, lat 12.975, lon 80.219, from 2023-12-03T18:00 to 2023-12-04T12:00 +05:30, in mm: `2.3, 1.4, 2.2, 1.6, 1.8, 1.9, 2.9, 2.5, 3.2, 2.8, 1.2, 3.4, 6.5, 11.5, 14.5, 14.4, 12.1, 9.4, 8.9`.

- Produces, in `fixtureSource.ts`: `createFixtureSource(opts?: { decidedBy?: Record<string, string> }): NimbusSource`.
  - `mode 'fixtures'`, `runs() → ['replay-michaung']`.
  - Every per-Run call returns the fixtures plus the scene for `replay-michaung`, and `[]` for any other Run.
  - `proposals` returns the fixture Work Order and `SCENE_WARD_ALERT`, with in-memory decisions applied.
  - `activity(run, since)` treats the cursor as the index of the next item (string), returns items after it and the new cursor, and returns `cursor: null` once nothing is left.
  - `decide` follows the API:
    - unknown id → `DecisionError('proposal_not_found')`;
    - a repeat of the same decision by the same officer returns the stored Proposal;
    - any other decision on a decided Proposal → `DecisionError('already_decided', …, { current_status, decided_by })`;
    - `edited` without an action, or `approved`/`rejected` with one → `'invalid'`;
    - otherwise set `status`, `decided_by`, `decided_at = created_at`, and `action` when edited.
  - `opts.decidedBy` pre-decides Proposals for tests: `{ 'pr-0001': 'officer-2' }` marks pr-0001 approved by officer-2.
  - `replay` is a local in-memory control, starting `{ playing: false, speed: 60 }`.
  - `rain('replay-michaung')` returns `MICHAUNG_RAIN`.
  - `commander` throws `'commander not configured'` until Task 10 wires it.

- [ ] **Step 1: Write the failing tests** in `fixtureSource.test.ts`:
  - `serves the fixture scene for replay-michaung`: 21 risk rows, 3 resources, 1 SOS, 2 proposals, 1 hazard, 1 reading.
  - `serves nothing for another Run`: every per-Run call on `'live'` → `[]`, and activity → `{ items: [], cursor: null }`.
  - `pages activity with an exclusive cursor`: the first call returns 8 items; calling again with the returned cursor returns 0 items.
  - `approves a pending Proposal`: status `approved`, `decided_by: 'officer-1'`.
  - `repeat of the same decision by the same officer is idempotent`.
  - `rejects a different decision with already_decided`: an error with code `already_decided` and `detail.decided_by === 'officer-1'`.
  - `pre-decided Proposals report the other officer`: `decidedBy: { 'pr-0001': 'officer-2' }`, then approve as officer-1 → `already_decided` with `decided_by: 'officer-2'`.
  - `validates edited actions`: `edited` with no action → `invalid`; `approved` with an action → `invalid`.
  - `unknown proposal`: `proposal_not_found`.
- [ ] **Step 2:** `npm test`. The new tests fail.
- [ ] **Step 3: Implement** `source.ts`, `fixtureScene.ts` and `fixtureSource.ts` as specified.
- [ ] **Step 4:** `npm test`, typecheck, lint. All pass.
- [ ] **Step 5: Commit.** `Add the console data source and fixture scene`

---

### Task 4: HTTP source and source selection

**Files:**
- Create: `src/config.ts`, `src/data/httpSource.ts`, `src/data/createSource.ts`, `src/data/httpSource.test.ts` and `src/config.test.ts`

**Interfaces:**
- Produces:

```ts
// config.ts
export type Config = { apiUrl: string | null; citizenApiUrl: string | null; officerId: string; officerName: string;
                       wardName: string; runs: string[]; runId: string };
export function readConfig(env: Record<string, string | undefined>, search: string): Config;
// defaults: officerId 'officer-1', officerName 'K. Priya', wardName 'Velachery', runs ['replay-michaung','live'],
// runId = ?run= value or runs[0]; trailing slashes trimmed from URLs; empty strings → null
// httpSource.ts
export function createHttpSource(cfg: Config, fetchFn?: typeof fetch): NimbusSource;
// createSource.ts
export function createSource(cfg: Config): NimbusSource;   // apiUrl ? http : fixtures
```

- HTTP behaviour (`api/README.md`):
  - `GET {apiUrl}/risk?run_id=…`, and the same for `/readings`, `/hazards`, `/resources` and `/sos`.
  - `GET {apiUrl}/proposals?run_id=…` (no status filter).
  - `GET {apiUrl}/activity?run_id=…&since=…&limit=500`, with `since` omitted when it is null.
  - `POST {apiUrl}/proposals/{id}/decision` with JSON `{ run_id, decision, decided_by, action? }`.
  - Segments: `GET {citizenApiUrl}/segments` when it is set, else the fixture `segments.json`.
  - `runs()` returns `cfg.runs`.
  - `rain(run)` returns `MICHAUNG_RAIN` for `replay-michaung`, else `[]`.
  - `replay` is the same local control as the fixture source (extract it to `createLocalReplay()` in `fixtureSource.ts` and reuse it).
- Error mapping for `decide`:
  - 404 → `proposal_not_found`.
  - 409 → `already_decided`, with `detail` from the body's `current_status` and `decided_by`.
  - 422 → `invalid`.
  - 502 → `event_not_sent`.
  - A network failure → `network`.
  - Other GET failures throw a plain `Error` with the status.

- [ ] **Step 1: Write the failing tests:**
  - `readConfig defaults`: an empty env and empty search give the defaults, `runId 'replay-michaung'`.
  - `readConfig reads ?run= and trims URLs`: `VITE_NIMBUS_API='https://x/'` gives `apiUrl 'https://x'`; `?run=live` gives `runId 'live'`.
  - `createSource picks fixtures without an API URL` (mode `fixtures`) and `http with one` (mode `http`).
  - `http GETs carry run_id`: a mocked fetch records the URL `https://x/risk?run_id=replay-michaung`.
  - `http activity omits since on first call and passes cursor after`.
  - `http decide posts the documented body`: the body equals `{ run_id: 'replay-michaung', decision: 'approved', decided_by: 'officer-1' }`, with no `action` key.
  - `http decide maps 409 with detail`: a mocked 409 `{error:'already_decided', current_status:'approved', decided_by:'officer-2'}` gives code `already_decided` and `detail.decided_by 'officer-2'`.
  - `http decide maps 502 to event_not_sent`, and a fetch rejection to `network`.
  - `segments come from the citizen API when configured`: `https://c/segments` is fetched.
- [ ] **Step 2:** `npm test`. The new tests fail.
- [ ] **Step 3: Implement** as specified.
- [ ] **Step 4:** `npm test`, typecheck, lint. All pass.
- [ ] **Step 5: Commit.** `Add the console HTTP source behind VITE_NIMBUS_API`

---

### Task 5: Query layer

**Files:**
- Create: `src/data/queries.tsx`, `src/test/fakeSource.ts`, `src/data/queries.test.tsx`

**Interfaces:**
- Consumes: `NimbusSource`, `DecisionError`, `Config`.
- Produces:

```ts
export function SourceProvider(props: { source: NimbusSource; config: Config; client?: QueryClient; children: ReactNode }): JSX.Element;
export function useSource(): NimbusSource;
export function useConfig(): Config;
export type ConsoleData = { segments: Segment[]; risk: SegmentRisk[]; readings: Reading[]; hazards: Hazard[];
  resources: Resource[]; sos: SosRow[]; proposals: Proposal[]; events: Event[]; rain: RainPoint[];
  clock: string | null; isLoading: boolean };
export function useConsoleData(): ConsoleData;   // uses config.runId
export function useDecide(): (proposalId: string, input: DecisionInput) => Promise<Proposal>;
export function useSyncStatus(): { secondsAgo: number | null; reconnecting: boolean };
// fakeSource.ts
export function fakeSource(overrides?: Partial<NimbusSource>, opts?: { decidedBy?: Record<string, string> }): NimbusSource; // createFixtureSource(opts) with overrides spread on top
```

- Heartbeat: one query `['heartbeat', runId]` with `refetchInterval: 2000` and `retry: false`. It fetches proposals, risk, resources, sos and activity together. Activity accumulates across heartbeats in a ref keyed by `runId` (dedupe by `event_id`; keep the cursor).
- Hazards and readings use `refetchInterval: 10000`. Segments and rain use `staleTime: Infinity`.
- `clock = stormClock([...risk.map(r => r.sim_time), ...events.map(e => e.sim_time)])`.
- `useSyncStatus` counts consecutive heartbeat failures. `reconnecting` is true at 2 or more. `secondsAgo` is the wall-clock seconds since the last success, re-rendered every 1 s.
- `useDecide`:
  - optimistically sets the Proposal's status in the heartbeat cache;
  - on `already_decided` it writes `current_status` and `decided_by` from the error detail into the cache, then rethrows;
  - on `event_not_sent` it retries once, then rethrows;
  - on any other error it restores the previous cache and rethrows;
  - it invalidates the heartbeat when done.

- [ ] **Step 1: Write the failing tests.** Use `renderHook` with a `SourceProvider` around `fakeSource()`, a fresh `QueryClient` and `vi.useFakeTimers({ shouldAdvanceTime: true })` where polling matters:
  - `loads the fixture scene`: `proposals.length === 2`, `events.length === 8`, `clock === '2023-12-04T02:00:00+05:30'`.
  - `empty Run gives empty data and a null clock`: config `runId 'live'`.
  - `optimistic approve then confirmed`: after `decide('pr-0001', {decision:'approved', decided_by:'officer-1'})`, `proposals` shows pr-0001 `approved`.
  - `already_decided writes the other officer into the cache and throws`: `fakeSource({ decide: () => Promise.reject(new DecisionError('already_decided','x',{current_status:'approved',decided_by:'officer-2'})) })` → it throws, and the cached pr-0001 has `decided_by 'officer-2'`.
  - `network error rolls back`: the cached pr-0001 is `pending` again.
  - `event_not_sent retries once`: `decide` is called twice; it succeeds on the second call.
  - `two failed polls mark reconnecting, then recovery clears it` (Review Focus 4): `proposals` rejects twice, then resolves. `reconnecting` goes true, then false, with `secondsAgo === 0`.
- [ ] **Step 2:** `npm test`. The new tests fail.
- [ ] **Step 3: Implement** as specified.
- [ ] **Step 4:** `npm test`, typecheck, lint. All pass.
- [ ] **Step 5: Commit.** `Add the console query layer with a 2 s heartbeat`

---

### Task 6: App layout, selection, shortcuts and top bar

**Files:**
- Create: `src/state/selection.tsx`, `src/state/shortcuts.ts`, `src/ui/icons.tsx`, `src/ui/TopBar.tsx`, `src/ui/RunSwitcher.tsx` with their CSS modules, `src/App.module.css`, and tests `src/state/shortcuts.test.tsx` and `src/ui/TopBar.test.tsx`
- Modify: `src/App.tsx`, `src/main.tsx`

**Interfaces:**
- Produces:

```ts
// selection.tsx
export type MapTarget = { kind: 'segment' | 'hazard' | 'resource' | 'sos'; id: string };
export function SelectionProvider(props: { children: ReactNode }): JSX.Element;
export function useSelection(): { proposalId: string | null; selectProposal(id: string | null): void;
                                  target: MapTarget | null; inspect(t: MapTarget | null): void };
// shortcuts.ts
export function useShortcuts(bindings: Record<string, (e: KeyboardEvent) => void>): void;
// keys are KeyboardEvent.key values ('a','e','r','/',' ','Escape'), matched case-insensitively;
// ignored when the event target is input, textarea, select or contenteditable, or when a modifier (ctrl, meta, alt) is held
// icons.tsx: WaveMark, Chevron, Pump, Crew, Hazard, Play, Pause, Check — each (props: { size?: number; color?: string }) => JSX.Element
```

- `App.tsx` is a grid: 56 px top bar, then columns of 384 px, `minmax(0,1fr)` and 344 px. The middle column has the map and a 92 px Replay bar. Use the min sizes from the mockup. For now, put placeholder `<aside>` and `<main>` regions labelled `Decisions`, `Map` and `Activity` (`aria-label`); later tasks replace them.
- `main.tsx` builds `readConfig(import.meta.env, location.search)`, then `createSource`, then `SourceProvider`, then `SelectionProvider`, then `App`.
- TopBar, using the mockup's markup and spacing:
  - the WaveMark and "NIMBUS", a divider, `{wardName} ward`;
  - the RunSwitcher: a button with a tag ("Replay" in `--watch` for `replay-*`, "Live" in `--teal` for `live`) and the Run name (`replay-michaung` → "Cyclone Michaung"; other names title-cased after `replay-`). It opens a listbox of `source.runs()`, and choosing one sets `?run=` with `location.assign`;
  - the clock (`formatClock(clock)`, or "—" when null);
  - the sync state: "Updated {n} s ago" with a teal dot, or "Reconnecting…" with an amber dot;
  - the officer's name.

- [ ] **Step 1: Write the failing tests:**
  - `shortcuts fire on keys`: pressing `a` calls the binding.
  - `shortcuts ignore typing` (Review Focus 2): with focus in an `<input>`, pressing `a` calls nothing.
  - `shortcuts ignore modifiers`: Ctrl+A calls nothing.
  - `TopBar shows the fixture clock and Run`: the text includes `02:00`, `Mon 4 Dec 2023`, `Replay`, `Cyclone Michaung`, `Velachery ward` and `K. Priya`.
  - `TopBar shows a dash for an empty Run`: with `runId 'live'` the clock reads `—` and the tag reads `Live`.
  - `RunSwitcher lists source runs`: opening it shows an option `Cyclone Michaung`.
- [ ] **Step 2:** `npm test`. The new tests fail.
- [ ] **Step 3: Implement** as specified.
- [ ] **Step 4:** `npm test`, typecheck, lint and build pass. Run `npm run dev` and check the top bar against the mockup.
- [ ] **Step 5: Commit.** `Add the console layout, top bar and Run switcher`

---

### Task 7: Decisions panel

**Files:**
- Create: `src/ui/DecisionsPanel.tsx`, `src/ui/DecisionCard.tsx`, `src/ui/DecisionEditor.tsx` with their CSS modules, and the test `src/ui/DecisionsPanel.test.tsx`
- Modify: `src/App.tsx` (replace the Decisions placeholder; the panel holds the Decisions, SOS and Resources sections, and the last two arrive in Task 8)

**Interfaces:**
- Consumes: `useConsoleData`, `useDecide`, `useConfig`, `useSelection`, `useShortcuts`, and the domain functions from `proposals.ts`.
- Produces: `DecisionsPanel(): JSX.Element` and `PanelSection(props: { title: string; count?: number; countTone?: 'teal' | 'sos'; hint?: string; children })`, which Task 8 reuses.

Behaviour (design.md "Left panel → Decisions"):
- **Cards.** Pending cards appear in rank order. The first pending card is selected on mount. Selecting a Work Order calls `inspect({kind:'segment', id: segment_id})`; a Ward Alert does not.
- **Card content:**
  - Kicker: the kind label ("Work Order" or "Ward Alert") and `{Proposer} · {hhmm(created_at)}`, with the proposer capitalised. A Ward Alert's kicker shows a "Held by Cedar" tag instead.
  - Title from `proposalTitle`, then the `reason`.
  - A Work Order shows the facts row: `{buildings}` buildings, `{Depth}` depth (capitalised; "—" when null) and `{reports}` Reports.
  - A Ward Alert shows the English draft and the Tamil draft (`lang="ta"`, Noto Sans Tamil).
- **Buttons.**
  - Approve is primary, with a `kbd` hint "A" on the selected card only. Edit and Reject are secondary.
  - Shortcuts `a`, `e` and `r` act on the selected card.
  - Reject shows an inline "Reject this Proposal?" with "Reject" and "Cancel".
- **Editing.** Edit opens `DecisionEditor` in the card.
  - A Work Order gets a `<select>` labelled "Resource" with the free Resources of the same `kind` as the current one, current first.
  - A Ward Alert gets two `<textarea>`s labelled "English" and "Tamil".
  - "Save and approve" posts `edited` with the full action (`kind` set). "Cancel" closes the editor.
- **After a decision,** the card shows `confirmationLine(...)` in teal with a Check icon, and the count updates.
- **Errors:**
  - `already_decided` replaces the buttons with `Already {status} by {deciderName(...)}`.
  - `event_not_sent` (after the hook's retry) shows "Saved, but the alert didn't go out." with a "Retry" button that calls decide again.
  - Any other error restores the buttons and shows "Couldn't send. Try again." under them.
- **"Decided (n)"** is a collapsed toggle row under the pending cards. Expanded, it lists each decided Proposal's title and `confirmationLine`.
- **Empty state:** "Nothing needs you right now."

- [ ] **Step 1: Write the failing tests.** Render `<SourceProvider source={fakeSource(...)}><SelectionProvider><DecisionsPanel/></SelectionProvider></SourceProvider>` with user-event:
  - `renders both fixture Proposals in rank order with the Work Order facts`: the headings are `Send Pump 2 to Velachery Main Road`, then `Ward Alert to everyone in Velachery`. The text includes `17`, `Knee` and `Held by Cedar`. The Tamil draft has `lang="ta"`.
  - `approve shows the confirmation line and drops the count`: click Approve → `Approved by K. Priya · Pump 2 en route`, and the count chip reads `1`.
  - `A approves the selected card`.
  - `reject asks first`: click Reject → `Reject this Proposal?`; Cancel → the buttons are back; Reject → Reject → `Rejected by K. Priya`.
  - `editing a Work Order offers only free pumps`: the select's options are exactly `['Pump 2']` (Tree crew 1 is excluded as another kind, Pump 1 because it is working).
  - `editing a Ward Alert posts edited text`: change English to `Avoid Velachery Main Road.`, then Save and approve → the source's `decide` received `{ decision: 'edited', action: { kind: 'ward_alert', message_en: 'Avoid Velachery Main Road.', … } }`.
  - `409 shows who decided` (Review Focus 1): `fakeSource({}, { decidedBy: { 'pr-0001': 'officer-2' } })`, click Approve → `Already approved by officer-2`, and no "en route" text.
  - `event_not_sent offers retry`: decide rejects with `event_not_sent` twice → the text `Saved, but the alert didn't go out.` and a Retry button.
  - `empty state`: a source whose `proposals` resolves `[]` → `Nothing needs you right now.`
  - `selecting a Work Order inspects its Segment`: a test probe that reads `useSelection().target` shows `segment:27480309-1` after mount.
- [ ] **Step 2:** `npm test`. The new tests fail.
- [ ] **Step 3: Implement** as specified, matching the mockup's card styles (`.dec`, `.facts`, `.draft`, `.approve`, `.sec-btn`).
- [ ] **Step 4:** `npm test`, typecheck, lint and build pass. Check visually in `npm run dev`.
- [ ] **Step 5: Commit.** `Add the Decisions queue with approve, edit and reject (#20)`

---

### Task 8: SOS and Resources sections

**Files:**
- Create: `src/ui/SosSection.tsx`, `src/ui/ResourcesSection.tsx` with their CSS modules, and the test `src/ui/LeftSections.test.tsx`
- Modify: `src/ui/DecisionsPanel.tsx` (render both sections after the Decisions section)

**Interfaces:**
- Consumes: `PanelSection`, `useConsoleData`, `useSelection`, `nearestSegment`, `streetName`, `minutesBetween`, `sosFlagsText`.

Behaviour:
- **SOS.** The header reads "SOS", with a count in the `sos` tone and the hint "Ranked by Triage". Rows are ranked first (by `rank`), then by `created_at`.
  - Each row reads `{street} · {people_count} people`. The sub-line is `{flags} · waiting {n} min`, without the flags part when there are none; `n` = `minutesBetween(created_at, clock)`.
  - An "Open" tag sits on the right. Clicking a row calls `inspect({kind:'sos', id})`.
  - Empty state: "No open SOS."
- **Resources.** The hint reads `{free} of {total} free`.
  - Each row shows the label, a sub-line "Near {street}", and a tag: Free in teal, En route as a teal outline, Working in muted grey.
  - Clicking a row calls `inspect({kind:'resource', id})`.

- [ ] **Step 1: Write the failing tests:**
  - `SOS row reads the fixture call`: compute `street = streetName(nearestSegment(sos.location, segments)!)` in the test, then expect the text `${street} · 3 people`, plus `Elderly resident · waiting 5 min` and `Open`.
  - `Resources show 2 of 3 free with tags`: `2 of 3 free`, Pump 1 → `Working`, Pump 2 → `Free`.
  - `clicking a resource inspects it`: the probe shows `resource:rs-pump-2`.
  - `empty SOS state`.
- [ ] **Step 2:** `npm test`. The new tests fail.
- [ ] **Step 3: Implement** as specified.
- [ ] **Step 4:** `npm test`, typecheck, lint and build pass.
- [ ] **Step 5: Commit.** `Add the SOS and Resources sections`

---

### Task 9: Activity feed

**Files:**
- Create: `src/domain/activity.ts`, `src/domain/activity.test.ts`, `src/ui/ActivityPanel.tsx`, `src/ui/FeedRow.tsx` with their CSS modules, and `src/ui/ActivityPanel.test.tsx`
- Modify: `src/App.tsx` (replace the Activity placeholder)

**Interfaces:**
- Produces:

```ts
// domain/activity.ts
export type FeedItem =
  | { kind: 'agent'; id: string; time: string; agent: Agent; decided: string; saw: string; why: string }
  | { kind: 'cedar'; id: string; time: string; principal: Agent; action: string; reason: string }
  | { kind: 'officer'; id: string; time: string; who: string; text: string }
  | { kind: 'commander'; id: string; time: string | null; question: string; answer: string; streaming: boolean };
export type FeedFilter = 'all' | 'cedar' | Agent;
export function toFeedItems(events: Event[], decided: Proposal[],
  ctx: ProposalContext & { officerId: string; officerName: string }): FeedItem[];
// newest first by instant; agent.activity → agent; policy.decided allowed:false → cedar; allowed:true dropped;
// other event types dropped; each decided Proposal → officer item at decided_at:
//   text `Approved the Work Order: ${title}.` / `Approved the Ward Alert.` / `Rejected: ${title}.`
//   ('Edited and approved' for edited); who = deciderName(...)
export function filterFeed(items: FeedItem[], f: FeedFilter): FeedItem[]; // 'cedar' keeps cedar; an Agent keeps that agent's agent items; commander items always kept
export const AGENT_LABEL: Record<Agent, string>;  // Sentinel, Verifier, Triage, Pathfinder, Dispatcher, Herald, Chronicler, Commander
```

- `ActivityPanel` accepts `extra: FeedItem[]` (the commander items, owned by Task 10) and merges them in. Commander items without a time sit at the top in insertion order.
- **Rows**, using the mockup's styling:
  - the time (`hhmm`) in the left column;
  - the agent label, with a "Held" tag on Cedar rows;
  - one sentence: `decided`, `reason` or `text`;
  - officer rows have a teal name.
- **Clicking an agent row** toggles a muted "Saw: … / Why: …" block.
- **Header filter.** "All agents ▾" opens a listbox: All agents, Cedar, then each agent in the feed.
- **New rows.** When the scroll container's `scrollTop > 0` and new items arrive, show a "{n} new" pill at the top. Clicking it scrolls to the top and clears it.

- [ ] **Step 1: Write the failing tests:**
  - `toFeedItems builds the fixture feed`: 7 items (8 events minus the allowed policy decision), newest first. The first is the cedar item with reason `Stopped the Herald's ward-wide alert until an officer approves it.`; the last is the pathfinder item.
  - `toFeedItems adds officer rows from decided Proposals`: pr-0001 approved by officer-1 at `2023-12-04T02:00:00+05:30` → an officer item `K. Priya` / `Approved the Work Order: Send Pump 2 to Velachery Main Road.`
  - `filterFeed narrows to Cedar and to one agent`.
  - `ActivityPanel shows Held on the Cedar row and expands an agent row`: clicking the Verifier "Merged 3 Reports…" row shows `Saw:`.
  - `approving in the store adds an officer row`: approve pr-0001 through the source, re-render → the text `Approved the Work Order: Send Pump 2 to Velachery Main Road.`
- [ ] **Step 2:** `npm test`. The new tests fail.
- [ ] **Step 3: Implement** as specified.
- [ ] **Step 4:** `npm test`, typecheck, lint and build pass.
- [ ] **Step 5: Commit.** `Add the agent Activity feed with Cedar and officer rows (#20)`

---

### Task 10: Ask the Commander

**Files:**
- Create: `src/domain/commander.ts`, `src/domain/commander.test.ts`, `src/data/fixtureCommander.ts`, `src/ui/AskCommander.tsx` with its CSS module, and `src/ui/AskCommander.test.tsx`
- Modify: `src/data/createSource.ts` (attach the commander), `src/ui/ActivityPanel.tsx` (render the commander block), `src/App.tsx`

**Interfaces:**
- Produces:

```ts
// domain/commander.ts
export type Snapshot = { risk: SegmentRisk[]; segments: Segment[]; proposals: Proposal[]; events: Event[];
                         sos: SosRow[]; resources: Resource[]; readings: Reading[]; clock: string | null; wardName: string };
export function buildCommanderAnswer(question: string, s: Snapshot): string;
// fixtureCommander.ts
export function registerSnapshot(fn: () => Snapshot): void;        // SourceProvider registers a getter over the query cache
export function createFixtureCommander(opts?: { delayMs?: number }): CommanderClient; // reads the registered getter at ask() time
// streams buildCommanderAnswer word by word (a word plus its trailing space per chunk), delayMs default 35
```

- `buildCommanderAnswer` is deterministic and grounded only in the snapshot. Three short paragraphs:
  1. **What changed:** the count of agent and Cedar items in the hour before `clock`, plus the two most recent `decided` texts.
  2. **What's waiting:** the count of pending Proposals and the title of each.
  3. **Top risk:** the flooded Segments' streets, then the count of `likely` Segments and the highest-scoring one's street and top reason.

  With an empty snapshot it returns "Nothing has happened in this Run yet."
- `createSource` sets `source.commander = createFixtureCommander()` in both modes, and `fakeSource` does the same. `SourceProvider` calls `registerSnapshot` with a getter that reads `useConsoleData`'s latest values and `config.wardName`.
- `AskCommander`:
  - an input labelled "Ask the Commander" with the placeholder "What changed in the last hour?" and a `kbd` "/";
  - `/` focuses it; Enter submits;
  - it is disabled while streaming;
  - it pushes a `commander` FeedItem into App state that `ActivityPanel` renders as a raised card: the question in muted text, then the answer filling in.

- [ ] **Step 1: Write the failing tests:**
  - `answer mentions the pending titles and the flooded street`: the answer for the fixture snapshot contains `Send Pump 2 to Velachery Main Road`, `Ward Alert to everyone in Velachery` and `Velachery Main Road`.
  - `empty snapshot answer`.
  - `fixture commander streams the whole answer`: after `registerSnapshot(() => snap)`, joining the chunks of `createFixtureCommander({ delayMs: 0 }).ask(q, run)` equals `buildCommanderAnswer(q, snap)`.
  - `/ focuses the input and A typed there does not approve` (Review Focus 2): in a full `<App/>` with fakeSource, press `/`, type `a` → the input value is `a` and pr-0001 is still pending.
  - `submitting shows the question and streamed answer in the feed, input disabled until done`.
- [ ] **Step 2:** `npm test`. The new tests fail.
- [ ] **Step 3: Implement** as specified.
- [ ] **Step 4:** `npm test`, typecheck, lint and build pass.
- [ ] **Step 5: Commit.** `Add Ask the Commander with a fixture Commander (#27)`

---

### Task 11: Map, layers and inspector

**Files:**
- Create: `src/ui/map/basemap.ts`, `src/ui/map/layers.ts`, `src/ui/map/MapView.tsx`, `src/ui/map/Inspector.tsx`, `src/ui/map/MapOverlays.tsx` with their CSS modules, `src/test/maplibre.ts`, and tests `src/ui/map/Inspector.test.tsx` and `src/ui/map/MapView.test.tsx`
- Modify: `src/App.tsx` (replace the Map placeholder)

**Interfaces:**
- Produces:

```ts
// basemap.ts
export const STYLE_URL = 'https://tiles.openfreemap.org/styles/fiord';
export function recolourBasemap(map: maplibregl.Map): void;   // the mockup's recolour() rules and colours
// layers.ts
export type LayerKey = 'risk' | 'readings' | 'hazards' | 'resources' | 'sos';
export function addNimbusLayers(map: maplibregl.Map, data: { segments: GeoJSON.FeatureCollection; nogo: GeoJSON.FeatureCollection }): void;
// sources 'segments', 'nogo'; layers 'seg-case', 'seg', 'nogo-fill', 'nogo-line'
export function updateNimbusData(map: maplibregl.Map, data: { segments: GeoJSON.FeatureCollection; nogo: GeoJSON.FeatureCollection }): void;
export function setLayerVisible(map: maplibregl.Map, key: LayerKey, visible: boolean): void; // risk → seg, seg-case; hazards → nogo-*; resources/sos → marker elements hidden via class; readings → segment colour expression without flooded→cyan
// Inspector.tsx
export function Inspector(props: { target: MapTarget; data: ConsoleData; showReadings: boolean }): JSX.Element;
// MapView.tsx
export function MapView(): JSX.Element;
```

- **Segment paint** (from the mockup):
  - casing `#0A1F44`, width interpolated from 6 at zoom 14 to 16 at zoom 18;
  - line colour `['match', ['get','band'], 'flooded', BAND_COLOR.flooded, …]`, opacity 0.45 for low, width from 3 at zoom 14 to 10 at zoom 18, `line-sort-key` on score.
- **Pins** are HTML markers (`.mk` classes from the mockup). **Never set `position` on the marker element.** MapLibre positions it absolutely, and overriding that misplaces every pin.
  - A Hazard is a diamond with "!" plus the no-go ring from `circlePolygon(location, no_go_radius_m)`.
  - A Resource is a rounded square with the Pump or Crew icon: a teal border when free, `--muted` when working, a dashed teal border when en route.
  - An SOS is a red circle with the people count and a ring pulse.
  - Labels show on hover.
- **Clicks.** Clicking a Segment line or a pin calls `inspect(...)`. When `target` changes, `flyTo({ center, zoom: 17.2 })` and open one `maplibregl.Popup` (offset 16, max width 300 px) whose DOM node renders `<Inspector>` through `createPortal`. Esc or the popup's close button calls `inspect(null)`.
- **Initial camera:** `fitBounds` over all Segment coordinates, padding 60.
- **Inspector content** (design.md "The inspector"):
  - **Segment:** `streetName`, `Segment {id}`, a band tag with `BAND_LABEL` (for flooded, "Flooded · Reading"), stats for Risk Score, time to flood ("Now" when flooded, `{n} min`, or "—" when null) and the mm threshold. When flooded and `showReadings` is on, the Reading line reads `Reading: {depth}-deep · confidence {c} · {k} Reports`. Then the numbered reasons.
  - **Hazard:** `HAZARD_LABEL`, owner, status, `Detected {hhmm}`, `No-go {r} m`.
  - **Resource:** label, kind, status, near street.
  - **SOS:** people, flags, waiting minutes, then rank and reasons when ranked.
- **MapOverlays:**
  - layer toggles, top left: buttons with `aria-pressed`, for Risk, Readings, Hazards, Resources and SOS;
  - the legend, bottom left: Flooded, Likely, Watch, Low;
  - zoom, bottom right: `NavigationControl` with `showCompass: false`;
  - compact attribution.
- **`src/test/maplibre.ts`** is a `vi.mock('maplibre-gl')` factory. Its fake `Map` records `addSource`, `addLayer`, `setPaintProperty`, `setLayoutProperty`, `flyTo` and `fitBounds`, fires `load` on the next tick, supports `on(event, layerId?, handler)` and has `getStyle() → { layers: [] }`. It also has a fake `Marker` (`setLngLat`, `addTo`, `remove`, `getElement`), a fake `Popup` (`setLngLat`, `setDOMContent`, `addTo`, `remove`, `on`) and a fake `NavigationControl`.

- [ ] **Step 1: Write the failing tests:**
  - `Inspector for the flooded Segment`: the text includes `Velachery Main Road`, `Segment 27480309-1`, `Flooded · Reading`, `92`, `Now`, `67.5`, `Reading: knee-deep · confidence 0.82 · 3 Reports`, and three reasons.
  - `Inspector for a watch Segment with null minutes shows a dash` (Review Focus 5): build a risk row with `minutes_to_flood: null` and band `watch` → `—`, and the band reads `Watch`, not "Flooded".
  - `Inspector falls back to Unnamed road`.
  - `Inspector hides the Reading line when readings are toggled off`.
  - `Inspector for the hazard`: `Open manhole`, `Corporation`, `No-go 30 m`.
  - `MapView adds Nimbus sources and layers after load`: the fake map recorded `addSource('segments')`, `addSource('nogo')` and layers `seg-case`, `seg`, `nogo-fill`, `nogo-line`.
  - `MapView flies to the selected Work Order's Segment`: after mount, `flyTo` was called with a center inside the 27480309-1 bbox.
  - `toggling Risk hides seg and seg-case`: `setLayoutProperty('seg','visibility','none')`.
- [ ] **Step 2:** `npm test`. The new tests fail.
- [ ] **Step 3: Implement** as specified.
- [ ] **Step 4:** `npm test`, typecheck, lint and build pass. Run `npm run dev` and check the real map: pins sit on their roads, the popup opens to the side and Esc closes it.
- [ ] **Step 5: Commit.** `Add the ward map with risk layers, pins and inspector (#11)`

---

### Task 12: Replay timeline

**Files:**
- Create: `src/domain/rain.ts`, `src/domain/rain.test.ts`, `src/ui/ReplayBar.tsx`, `src/ui/RainChart.tsx` with their CSS modules, and `src/ui/ReplayBar.test.tsx`
- Modify: `src/App.tsx` (render ReplayBar under the map only when `runId` starts with `replay-`; otherwise the map fills the column)

**Interfaces:**
- Produces:

```ts
// rain.ts
export type RainGeometry = { line: string; area: string; nowX: number | null; nowY: number | null; nowMm: number | null;
                             ticks: { x: number; label: string; anchor: 'start' | 'middle' | 'end' }[] };
export function rainGeometry(points: RainPoint[], nowIso: string | null, width: number, height: number): RainGeometry;
// x spans 0..width over the series; y from (height-16) at 0 to 14 at max(maxMm, 1); now = the point whose hour contains nowIso
// (null when outside the series); ticks: first ('18:00 · 3 Dec', start), each 00:00 and 06:00 inside ('00:00','06:00', middle), last ('12:00 · 4 Dec', end)
export const SPEEDS: ReplaySpeed[];   // [15, 30, 60, 120]
export function nextSpeed(s: ReplaySpeed): ReplaySpeed;  // cycles
```

- `RainChart` draws the mockup's SVG:
  - the future area `#21497D` at 45% opacity with a `#3E78A0` stroke;
  - the past, clipped at `nowX`, as area `#3E78A0` at 55% with a `#A9C6DB` stroke;
  - a white playhead with a dot;
  - the label `{hhmm(clock)} · {nowMm} mm/h`;
  - tick labels in `--faint`.

  It measures its width with a `ResizeObserver` (jsdom: fall back to 600).
- `ReplayBar`:
  - a play/pause button (`aria-label` "Play Replay" or "Pause Replay", Space toggles);
  - a speed button showing `{speed}×` that cycles through `nextSpeed`;
  - both call `source.replay.set(runId, …)` and render the returned state.

- [ ] **Step 1: Write the failing tests:**
  - `rainGeometry places now at 02:00 with 3.2 mm/h`: for `MICHAUNG_RAIN` and `'2023-12-04T02:00:00+05:30'` at width 900 → `nowMm 3.2`, and `nowX` is about `900 * 8/18`.
  - `rainGeometry with a clock outside the series has no playhead`.
  - `rainGeometry ticks`: the labels are `['18:00 · 3 Dec','00:00','06:00','12:00 · 4 Dec']`.
  - `nextSpeed cycles 120 → 15`.
  - `Space toggles play and the label flips`: `Play Replay`, then `Pause Replay`.
  - `speed button cycles 60× → 120×`.
  - `App hides the Replay bar on a live Run`.
- [ ] **Step 2:** `npm test`. The new tests fail.
- [ ] **Step 3: Implement** as specified.
- [ ] **Step 4:** `npm test`, typecheck, lint and build pass.
- [ ] **Step 5: Commit.** `Add the Replay timeline with Michaung rainfall (#20)`

---

### Task 13: Integration, visual check and hand-off

**Files:**
- Create: `src/App.test.tsx`
- Modify: `console/README.md`

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: Write the failing integration tests** in `App.test.tsx` (maplibre mocked):
  - `renders the whole fixture scene`: the Decisions, Map and Activity regions exist; the texts `Send Pump 2 to Velachery Main Road`, `Elderly resident`, `2 of 3 free` and `Stopped the Herald's ward-wide alert` appear, along with the `Pause Replay` or `Play Replay` button.
  - `empty Run renders empty states without errors` (Review Focus 3): `?run=live` with fixtures → `Nothing needs you right now.`, `No open SOS.`, the clock `—`, no Replay bar, and no `console.error` calls (spy on it).
  - `approve flows end to end`: press `a` → the card's confirmation line and the officer row in the feed both appear.
- [ ] **Step 2:** `npm test`. Fix anything the integration exposes until everything passes.
- [ ] **Step 3: Visual check.**
  - Run `npm run build && npx vite preview --port 4173`.
  - Take headless screenshots at 1920×1080 and 1280×800. Use Chromium through the DevTools protocol with a real-time wait of about 9 s, because `--virtual-time-budget` stalls tile loading. The scratchpad `shot.mjs` from the design session is the pattern.
  - Compare each against `docs/mockups/deep-tide-v2.html`, fix any difference, and record both screenshots in the PR.
- [ ] **Step 4: Update `console/README.md`.**
  - How to run it: `npm install`, `npm run dev`, the four check commands.
  - The env variables from `.env.example` and that fixture mode is the default.
  - The keyboard shortcuts.
  - A link to `docs/design.md`.
- [ ] **Step 5: Final verification.** `npm test && npm run typecheck && npm run lint && npm run build`. All pass, and the output is quoted in the PR.
- [ ] **Step 6: Commit.** `Wire the console end to end and document it`
- [ ] **Step 7: Open the issues** from design.md "Issues to open for other lanes" with `gh issue create`. Use the lane owner's label (`owner:varun`, `owner:goutam`, `owner:vishwa`) and the `needs-triage` label, and reference this branch's design doc.
- [ ] **Step 8: Push and open a PR** to `main` titled `Ward console on fixture data (#11, #20, #27 partial)`.
  - The body says `Closes #11`, and `Part of #20, #27`.
  - It lists what works on fixtures, what waits on other lanes (with the new issue numbers), and the screenshots.
  - It ends with the attribution line `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
