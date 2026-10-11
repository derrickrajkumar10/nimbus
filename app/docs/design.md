# NIMBUS citizen app: design

Owner: Derrick. Issues: #12 (shell, places, push), #21 (photo Report), #28 (route, SOS). Terms follow [CONTEXT.md](../../CONTEXT.md).

## Why

The citizen app is the half of NIMBUS that judges see on a phone. In the video it carries three beats: a Tamil alert to move a bike (0:35), a photo that comes back knee-deep with an open manhole (0:55), and a two-wheeler detour with its reason (1:20). It has to feel like a finished product, not a hackathon prototype. Anything that looks like generic AI output (emoji icons, stock gradients, filler copy) counts as a failure even if it works.

**Centrepiece:** the photo-to-depth reveal (screen 8). It gets the most polish. Everything else should be clean and solid.

## Goals

- An Android Flutter app in the **Deep tide** style (below), in English and Tamil.
- Real backend wherever it exists today: Segments, risk, Readings, devices, Saved Places, push.
- Every other screen works against `contracts/fixtures/` behind one setting, and moves to the real API as each route lands.
- It runs reliably on the demo phones for filming.

## Non-goals

- iOS (ADR 0002), offline mode, the at-risk registry, shelters, ambulance-to-hospital routing. These are roadmap items for the video only.
- Accounts or sign-in. A Reporter is an anonymous install (`X-Install-Id`), until #19.
- The ward console (`console/`), which is a separate project.

## Anti-goals

- No emoji or stock icon packs that look generic. Icons are drawn for this app (a consistent line set, 1.8 px stroke on a 24 px grid, as in the mockups).
- Never call a predicted Segment "flooded". Predicted risk uses warm colours (amber for watch, red for likely). Only an observed Reading is blue or cyan water.
- No fake "live" claims. Fixture mode must be one obvious setting in code, never mixed into real responses.

## Visual language: Deep tide

The chosen mockup is "2 · Deep tide" in `.superpowers/brainstorm/` (local only, not committed).

- **Background:** the sea. A gradient from storm sky `#5F8FAE` to deep `#0A1F44`, with layered illustrated waves (`#3E78A0`, `#2E6690`, `#22557F`, `#18456E`, `#10365E`, `#0A2849`). Thin rain streaks sit in the sky area.
- **Type:** Outfit for Latin text, Noto Sans Tamil for Tamil. Both fonts are bundled, never fetched at runtime.
- **Colour:** text white, muted `#A9C6DB`, accent teal `#4FD1D9` (buttons `#2FA9B8`), SOS `#E8432A`. Risk: low `#CFE3F0`, watch `#F2B34A`, likely `#FF7A57`. Observed water: `#59D8E6`.
- **Controls:** round 48 px buttons with a soft 6 px halo ring. The SOS button is red.
- **Motion:** waves drift slowly all the time, and changes in state move with the water. Respect the system's reduce-motion setting.

## Screens

1. **Intro (plays once).** An in-app animation of about 6 s: rain falls, the tide rises to fill the screen, then the NIMBUS wordmark appears with the Tamil tagline. It's skippable, and a flag stores that it has played.
2. **First run.** Pick a language (தமிழ் / English), allow notifications, and add the first place. A hidden demo switch puts the install in the `replay-michaung` Run, so its Saved Places are sent with `run_ids: ["replay-michaung"]`.
3. **Home.** Mockup layout: the wordmark, the Run and storm time, and a headline that says what to do ("2 of your places need you now"). Below it, each Saved Place sits on its own wave layer, ordered by severity, with the worst at the bottom. Each place shows its name, the reason or action line, and the band with a countdown. Bottom buttons: Report, Route, Map, SOS.
4. **Place detail.** A map around the place with its Segments coloured by band, the top three reasons from `SegmentRisk.reasons`, minutes to flood, and the action with "Show me the way", which opens Route. **The action line** is the body of the last alert received for this place (the Herald works out the safer street on the server). With no alert yet, it falls back to a band-based line ("Move your vehicle to higher ground"). The app never copies the Herald's logic.
5. **Add or edit a place.** Kind (`home`, `office`, `school`, `vehicle_parking`), a label, a pin dropped on the map, and a radius. Saved with `PUT /saved-places/{place_id}`. Delete is also available.
6. **Ward map.** Segments by band, Readings, and Hazard pins with their no-go rings. Polled while open.
7. **Alerts.** Register the FCM token with `POST /devices` at first run and on token refresh, sending the language. The push shows the title and body the sender chose. Its `data` holds `alert_id`, `run_id`, and optionally `segment_id` and `band`. Tapping it opens the Saved Place whose `segment_ids` contain that `segment_id`, or Home if none does. All-clear pushes come from the Herald, so the app has nothing extra to build for them.
8. **Photo Report: the centrepiece.** Camera, then compress, then submit. Then a staged reveal of about 6 s:
   1. the photo shrinks into a frame while "Verifying…" plays as ripples;
   2. water rises up a figure and settles at the depth band of the Reading (ankle, knee, waist, above waist), and the label fades in, in English and Tamil;
   3. the vehicle markers drop in one at a time (two-wheeler, car, ambulance) from `Reading.passable`;
   4. any `hazards_seen` appears as a pulsing red warning;
   5. the view pulls back to the map: the Segment turns to water and the Hazard ring appears. "You taught the map" counts the threshold from `Segment.baseline_threshold_mm` down to the current `SegmentRisk.flood_threshold_mm`. If the two are equal, the line instead says the Reading confirmed the prediction. The nudge comes from the risk engine under the rule Derrick decided (#60): the threshold drops to the rain at the time the water was seen, with a floor of 60% of the baseline. Until #60 lands, and always in fixture mode, the "confirmed" line shows.

   Waiting: stage 1 keeps rippling while the app polls `GET /readings?report_id=`. After about 30 s it says the Report is still being checked and that a push will follow. A rejected Report, or one with no Reading, gets a polite state that explains why.
9. **Safe route.** From and to (a Saved Place or a point on the map) and a vehicle (`two_wheeler`, `car`, `ambulance`). Shows the `RouteResponse` geometry, distance, time, `reason`, `reason_ta`, and the avoided streets and hazards. `no_safe_route` gets its own screen with the reason and no line.
10. **SOS.** People count, elderly, child and medical flags, sent with `POST /sos` and a client-made `sos_id`, so a retry is safe. Citizens can't read Triage's ranking, so the status card shows what was sent, when (storm time), and that the ward officers have it. The photo is left out because `POST /sos` has no photo field.
11. **Language.** The த button switches the whole app instantly, and the choice is sent to `POST /devices`. Server text: `SegmentRisk.reasons` are English with the numbers baked in, so in Tamil mode the app shows a Tamil line per reason `code` (`antecedent_rain`, `forecast_below_threshold`, `forecast_exceeds_threshold`, `heavy_rain`, `rain_exceeds_threshold`), falling back to the English text for an unknown code. Route reasons use `reason_ta` when present. Push text arrives already in the device's language.

## Data

- **Models:** the generated Dart classes in `contracts/generated/dart/nimbus.dart`. Never redefine an entity. `RankedSos` and the extra `run_ids` on Saved Places are the only shapes the API adds on top.
- **Real today** (citizen API, `api/README.md`): `GET /segments` (cache it, since it's static), `GET /risk`, `GET /readings?report_id=`, `POST /devices`, `GET`/`PUT`/`DELETE /saved-places`, `POST /reports/upload-url` then a `PUT` of the JPEG then `POST /reports`, `POST /sos`, and `POST /routes`. The base URL comes from SSM `/nimbus/api/citizen-url`.
- **Real but not live yet:** `POST /routes` returns 503 `routing_unavailable` until the Pathfinder exists (#23). A Reading appears only once the Verifier runs (#17). `/reports` and `/sos` return 409 `run_not_started` for a Replay that hasn't started. Each of these gets a clear screen state, never a crash.
- **Fixtures until built:** Hazards, because the citizen API has no `GET /hazards` yet (#58). Fixture mode also covers every route above for building and filming without a backend. Fixture data is `segments.json`, `risk.json`, `readings.json`, `hazards.json`, `routes.json` and `sos.json`, with a short simulated delay.
- **Generated models:** nullable fields are `T?` once #61 merges. Until then, build on that branch's `nimbus.dart`.
- **Data source:** one setting chooses fixtures or an API base URL, so each route can switch to real on its own as it lands.
- **Run:** every request carries `run_id` (`live` or `replay-michaung`). Domain timestamps shown to the user come from `sim_time`, never the phone clock.
- **Polling:** `GET /risk` every few seconds while Home, Map or Place detail is visible. A Replay runs one storm hour every 10 s.

## Constraints

- Android first. Flutter, `maplibre_gl` (issue #12). A dark map style tuned to Deep tide, using free vector tiles (for example OpenFreeMap).
- Only edit `app/`. Requests for other lanes become issues (CI job: Varun; `/reports`, `/routes`, `/sos`: Varun with the Verifier #17 and Pathfinder #23).
- Firebase config (`google-services.json`) comes from Varun and is never committed if it holds secrets.
- Flutter isn't installed on Derrick's machine yet. The Android SDK and Java 17 are.

## Calls made without Derrick (check these)

- The Android package is `com.nimbus.chennai` (as requested from Varun on #1).
- The manual "flag a hazard" option is cut, because no contract or route exists for it. Hazards come from photos via the Verifier.
- The SOS photo is cut (see screen 10).
- The action line comes from the last alert, not from logic copied into the app.
- Tamil reasons are mapped by code, without the numbers.

## Left to the builder

State management, folder layout, the animation technique (CustomPainter or similar), how fixtures are bundled into `app/` (assets can't live outside the package, so copy them with a script), the install-id format (it must meet the API's 8–80 character rule), the exact polling interval, and the tests worth writing (at least: sorting places by severity, mapping an alert to a place, and parsing every fixture through the generated models).
