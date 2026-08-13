# JavaFrank Fire / EMS Intelligence Mode
## Master Implementation Plan for Codex CLI

**Project:** JavaFrank / DFR Station Optimizer Lite
**Purpose:** Add a reusable Fire / EMS Intelligence Mode while preserving all existing General / non-fire functionality.
**Primary pilot dataset:** San Ramon Valley Fire Protection District (SRVFPD), 2025 calls.
**Implementation model:** One shared application, not a separate fire-only fork.

---

# 1. EXECUTION RULES

Codex must follow these rules throughout implementation.

1. Inspect the entire repository before changing code.
2. Preserve all existing General-mode behavior.
3. Do not create a separate fire-only `index.html` unless a compelling technical limitation requires it.
4. Prefer modular Fire-specific JavaScript over adding large blocks directly to `index.html`.
5. Never fabricate:
   - coordinates
   - response times
   - costs
   - medical outcomes
   - apparatus assignments
   - historical thermal observations
6. Clearly distinguish:
   - actual historical CAD data
   - modeled results
   - configurable assumptions
   - external/reference research
7. Fire-specific features must fail gracefully when required columns are absent.
8. Existing CAD ingestion, station optimization, maps, filters, exports, session save/load, and General mode must continue to work.
9. Maintain backwards compatibility with existing `.tank` sessions where practical.
10. Do not remove existing functionality merely because Fire mode introduces a better alternative.
11. Use Git-sized, reviewable implementation stages.
12. After each implementation stage:
    - run available tests/checks
    - test General mode
    - test Fire mode
    - report changed files
    - report known limitations
13. Do not proceed to the next stage if the current stage introduces regressions that can reasonably be fixed first.
14. Do not silently convert modeled metrics into statements of historical fact.

---

# 2. PRODUCT STRATEGY

JavaFrank should remain one reusable public-safety analysis application.

Conceptual product structure:

```text
JavaFrank
├── General Analysis
│   ├── Existing CAD workflow
│   ├── Existing station optimization
│   ├── Existing coverage analysis
│   └── Existing reporting
│
└── Fire / EMS Intelligence
    ├── Ground Response Coverage
    ├── Drone Response Coverage
    ├── Eyes Before Arrival
    ├── Thermal Intelligence
    ├── Fire / WUI
    ├── EMS / ALS
    ├── Resource Right-Sizing
    ├── Financial / Capacity Modeling
    ├── Community Impact
    └── Chief Presentation Mode
```

Customer-specific projects should be represented as saved sessions/presets, not separate application forks.

Example:

```text
SRVFPD_2025_Fire_Chief.tank
```

The San Ramon session may contain:
- 2025 CAD calls
- SRVFPD station roster
- Dispatch launch location
- proposed drone station(s)
- Fire / EMS mode enabled
- Fire assumptions
- report configuration
- presentation configuration

---

# 3. PRIMARY CUSTOMER PROBLEM

The Fire Chief presentation and report should answer:

> What can the department know before its people arrive?

Customer concerns to support:

- Fire resources are sometimes dispatched in larger numbers than ultimately required.
- Crews may arrive very quickly, approximately two minutes in some cases.
- Those first minutes are operationally important.
- A dispatch-launched drone could be airborne while crews are gearing up.
- Live video could be available while apparatus are still en route.
- Earlier scene awareness may help Dispatch and command staff adjust resource deployment.
- The pilot is expected to be dispatch-centered.
- Real-time video streaming is a major operational capability.
- Thermal imaging adds additional fire, WUI, search, rescue, and post-fire awareness.

The application should focus first on operational awareness, then resource/cost impact.

---

# 4. EVIDENCE CLASSES

Every Fire report must visibly separate three evidence classes.

## A. Actual Department Data

Examples:
- incident locations
- incident dates
- call types
- priorities
- actual timestamps, when present
- actual units, when present
- actual dispositions, when present

## B. JavaFrank Modeled Results

Examples:
- modeled drone travel time
- modeled ground travel time
- estimated drone lead time
- modeled apparatus miles avoided
- modeled operating impact
- modeled coverage gap

## C. Reference / Research Context

Examples:
- national apparatus/equipment rates
- medical literature
- thermal-imaging use cases
- community-impact research
- industry assumptions

Never visually mix these categories without labels.

---

# 5. DATA CAPABILITY MODEL

Fire mode must work across datasets with different levels of detail.

## Level 1 — Location-Only Fire CAD

Typical fields:
- incident number
- date
- call type
- priority
- latitude
- longitude

Capabilities:
- call-density analysis
- station proximity
- ground-access modeling
- drone coverage
- modeled ground-vs-air comparison
- Fire / EMS call categorization
- geographic gap analysis

Do NOT claim actual historical response times.

## Level 2 — Timestamp-Enabled CAD

Additional fields may include:
- call received
- dispatch
- turnout
- en route
- first arrival
- clear time

Capabilities:
- actual historical response-time analysis
- drone-first-arrival comparisons
- true lead-time distributions
- actual turnout/travel decomposition

## Level 3 — Unit / Apparatus CAD

Additional fields may include:
- unit identifier
- apparatus type
- assignment time
- cancellation
- arrival
- clear
- disposition

Capabilities:
- apparatus utilization
- multi-unit deployment
- cancellation/downgrade analysis
- crew/apparatus time modeling
- stronger financial/resource analysis

Build Fire mode so functionality increases automatically as richer data is available.

---

# 6. FIRE CALL CLASSIFICATION

Create a configurable Fire / EMS classification layer.

Suggested categories:

- Structure Fire
- Fire Alarm
- Smoke Investigation
- Outside Fire
- Vegetation / Wildland / WUI
- Vehicle Fire
- Electrical
- Hazardous Materials
- Gas / Odor
- Rescue
- Traffic Collision
- Medical
- ALS / High Acuity
- Cardiac Arrest
- Respiratory
- Unconscious
- Overdose
- Trauma
- Public Assist
- Other Fire
- Other EMS
- Unknown

Classification should:
- use normalized call type text
- support configurable aliases
- retain original CAD incident type
- avoid destructive re-labeling

---

# 7. FIRE STATION MODEL

Support official fire station CSV import.

Desired columns:

```text
station_id
station_name
agency
address
city
state
zip
latitude
longitude
station_type
staffing
notes
source_url
```

Requirements:
- support records with addresses but no coordinates
- do not invent missing coordinates
- clearly indicate ungeocoded stations
- preserve source URL
- allow stations to be toggled separately from proposed drone stations
- support neighboring/mutual-aid stations later

Primary SRVFPD station dataset should include Stations 30–39.

---

# 8. GROUND COVERAGE ANALYSIS

Add a Fire-specific ground-response layer.

At minimum support:
- nearest station by straight-line distance
- ground distance/time when a routing source is available
- configurable modeled ground speed when routing is unavailable
- configurable station turnout assumption
- 4 / 6 / 8 / 10 minute coverage thresholds

For each call calculate, when possible:

```text
nearest_station
ground_distance
modeled_ground_travel_time
modeled_ground_total_time
ground_coverage_band
```

Clearly label modeled results.

---

# 9. GROUND COVERAGE GAP

Create map and report classifications:

- Strong Ground Coverage
- Ground Coverage Gap
- Drone Opportunity
- Double Coverage
- Remaining Gap

Concept:

```text
Ground Coverage Gap:
Call exceeds selected modeled ground threshold.

Drone Opportunity:
Ground-gap call is inside drone service coverage.

Double Coverage:
Call is inside both strong ground and drone coverage.

Remaining Gap:
Call falls outside selected ground threshold and outside drone coverage.
```

Create clear map legend and filters.

---

# 10. DRONE RESPONSE MODEL

Configurable assumptions:

```text
launch_delay_seconds
cruise_speed_mph
max_radius_miles
minimum_useful_lead_seconds
dispatch_start_basis
```

Where actual timestamps are present:

```text
drone_arrival_time =
dispatch_time + launch_delay + modeled_flight_time

drone_lead_time =
first_ground_arrival - drone_arrival_time
```

Where actual timestamps are absent:

```text
modeled_air_advantage =
modeled_ground_total_time - modeled_drone_total_time
```

Never present modeled advantage as actual historical lead time.

---

# 11. EYES BEFORE ARRIVAL

This is a primary Fire KPI.

Preferred metric:

> Calls where live scene intelligence could potentially be available before first ground-unit arrival.

Suggested bands:

- 2+ minutes early
- 1–2 minutes early
- 30–60 seconds early
- 0–30 seconds early
- near tie
- ground first

Display:
- annual counts
- percentages
- map categories
- call-type breakdown
- station / launch-site breakdown

---

# 12. REAL-TIME VIDEO

Real-time video is operational value, not merely a hardware feature.

Report/presentation framing:

```text
Dispatch
→ Drone Launch
→ Live Video Available
→ Responders En Route
→ Scene Intelligence
→ First Ground Unit Arrival
```

Potential awareness examples:
- visible smoke
- visible flame
- roof involvement
- vehicle involvement
- scene access
- number of vehicles
- building exposure
- road blockage
- crowd conditions
- obvious false/low-severity conditions
- hazards visible from the air

Do not imply video can confirm conditions that are not visually observable.

---

# 13. THERMAL INTELLIGENCE

Thermal must be a distinct Fire capability layer.

Potential use cases:

## Structure Fire
- roof heat patterns
- exterior heat signatures
- fire extension indicators
- exposure monitoring
- hot-spot detection
- overhaul support

## Wildland / WUI
- active heat identification
- fire-edge awareness
- spot-fire search
- residual heat
- inaccessible terrain monitoring

## Search / Rescue
- nighttime search
- open-space search
- crash/ejection search
- embankment search
- missing/injured-person support

## Post-Fire
- residual hot spots
- re-ignition monitoring

Presentation UI should support:

```text
VISIBLE | THERMAL
```

Important disclaimer:
Thermal is not X-ray vision and does not see through walls. Performance depends on line of sight, environmental conditions, sensor capability, and interpretation.

Historical datasets without thermal imagery should show thermal as:
- capability context
- modeled opportunity
not historical observation.

---

# 14. WUI / WILDLAND MODE

Add Fire call filters and analytics for:
- vegetation fire
- outside fire
- smoke investigation
- illegal burn
- WUI incidents

Useful outputs:
- ground access challenge
- drone coverage
- thermal-capable coverage
- nearest ground station
- distance from drone launch
- modeled time advantage

Future enhancement:
- terrain/access difficulty layers where reliable data is available

---

# 15. EMS / ALS MODE

Do not use the same value framing as low-acuity Fire calls.

For high-acuity medical incidents emphasize:
- situational awareness
- access
- scene conditions
- responder preparation
- geographic coverage
- proximity to hospitals/trauma resources

High-acuity categories may include:
- cardiac arrest
- unconscious
- respiratory distress
- severe trauma
- overdose
- other locally defined ALS priorities

Do not claim lives saved unless a defensible causal model and medical evidence support that statement.

Preferred language:
- high-acuity calls covered
- potential earlier scene awareness
- time-to-information
- geographic access
- response-capacity preservation

---

# 16. HOSPITAL / MEDICAL CONTEXT

Support optional hospital dataset.

Desired columns:

```text
facility_name
facility_type
address
city
state
zip
latitude
longitude
trauma_level
emergency_department
notes
source_url
```

Potential display:
- emergency departments
- trauma centers
- call clusters
- distance from high-acuity incidents
- geographic gaps

Do not infer clinical capability without reliable source data.

---

# 17. RESOURCE RIGHT-SIZING

Only enable strong downgrade analysis when unit/apparatus/disposition data exists.

Potential indicators:
- multiple units initially assigned
- units canceled
- call downgraded
- no fire found
- alarm reset
- minor incident
- low-severity disposition
- resources released before arrival

Separate:

```text
Observed Historical Downgrade
```

from:

```text
Modeled Potential Right-Sizing Opportunity
```

Never treat a potential opportunity as an actual historical decision.

---

# 18. FINANCIAL / CAPACITY MODEL

Avoid simplistic claims such as:
"$X saved every time a truck does not respond."

Fire staffing is often fixed. Some benefits are capacity and wear rather than immediate cash savings.

Model separately:

## A. Avoidable Apparatus Miles

```text
avoidable_miles =
avoided_apparatus_count × modeled_round_trip_miles
```

## B. Avoidable Apparatus Time

```text
avoidable_apparatus_hours =
avoided_apparatus_count × avoided_response_time_hours
```

## C. Crew Capacity

```text
crew_hours_preserved =
avoidable_apparatus_hours × crew_size
```

## D. Modeled Operating Impact

Using configurable sourced rates:
- equipment rate
- mileage rate
- fuel
- maintenance / utilization proxy

## E. Capacity Returned

Highlight:
- unit-hours potentially preserved
- apparatus availability
- concurrent-call readiness
- reduced unnecessary emergency driving
- wear/utilization reduction

All rates must:
- be editable
- show source
- show year
- show units
- appear in export methodology

---

# 19. COMMUNITY IMPACT

Community-impact section may include:

- emergency-response capacity preserved
- fewer unnecessary emergency-vehicle miles
- improved availability for concurrent calls
- improved awareness before responder arrival
- high-acuity calls within drone coverage
- geographic gaps reduced by aerial response
- rural/WUI coverage support

Do not convert these into unsupported life-safety claims.

---

# 20. CHIEF PRESENTATION MODE

Create a presentation-focused interface separate from the detailed analyst controls.

Suggested toggle:

```text
Analysis Mode | Presentation Mode
```

Presentation Mode should use:
- large metrics
- minimal controls
- map-first storytelling
- real customer data
- smooth transitions
- explicit actual vs modeled labels

Do not remove Analysis Mode.

---

# 21. PRESENTATION STORY

Recommended five-minute story:

## Screen 1 — Customer Problem

Headline:

> What if Dispatch could see the scene before the first apparatus arrived?

Large metrics:
- total 2025 calls
- calls inside drone coverage
- modeled/actual drone-first opportunities
- median advance-awareness time, when supported

## Screen 2 — Annual Call Map

Show all customer calls.

Allow:
- Fire
- EMS
- ALS
- Structure Fire
- Alarm
- WUI
- Crash

## Screen 3 — Race to the Scene

For a selected actual call:

```text
DISPATCH 00:00

DRONE:
Launch → Flight → LIVE VIDEO

GROUND:
Tone → Turnout → Travel → ON SCENE
```

Display:

```text
DRONE LIVE: 01:08
GROUND ARRIVAL: 02:03
ADVANCE AWARENESS: 00:55
```

If only modeled ground timing exists, label the entire race as MODELED.

## Screen 4 — Two-Minute Window

Visualize:

```text
0:00 Dispatch
0:XX Drone Launch
0:XX Crew Gearing
1:XX Live Video
1:XX Apparatus En Route
2:00 First Arrival
```

Annual KPI:

> Calls where aerial scene intelligence could potentially become available during the first two minutes.

## Screen 5 — Ground Gap → Air Coverage

Show:
- ground coverage threshold
- calls outside ground threshold
- drone coverage overlay
- gaps covered by drone
- remaining gaps

## Screen 6 — Thermal

Toggle:

```text
VISIBLE | THERMAL
```

Display capability callouts based on incident type.

## Screen 7 — Resource Right-Sizing

For appropriate low-acuity incident example:

```text
Initial modeled/historical deployment:
Engine
Engine
Medic
Chief

Potential adjusted response:
Engine
Medic
```

Show:
- potential apparatus count reduced
- miles
- apparatus-hours
- crew-hours
- modeled operating impact

Only show if dataset supports a defensible model.

## Screen 8 — ALS / Life Safety

Switch away from cost.

Show:
- high-acuity call
- drone coverage
- ground coverage
- hospital context
- potential advance awareness

## Screen 9 — Executive Impact

Four major cards:

```text
EYES FIRST
X calls

CAPACITY
X apparatus-hours

COST / OPERATING IMPACT
$X modeled

HIGH-ACUITY COVERAGE
X calls
```

---

# 22. SIGNATURE VISUAL: RACE TO THE SCENE

This should be one of the application's highest-quality Fire visualizations.

Requirements:
- uses real call location
- real incident type
- actual timestamps if available
- otherwise explicitly modeled
- visual drone path
- visual ground station / ground path where available
- synchronized timing
- live-video milestone
- optional thermal milestone/capability
- replay
- next-call control

Filters:
- structure fire
- fire alarm
- EMS
- ALS
- crash
- WUI

---

# 23. SIGNATURE VISUAL: GROUND VS AIR ADVANTAGE

For each call classify:

- Air ≥2 min faster
- Air 1–2 min faster
- Air 0–1 min faster
- Near tie
- Ground faster

When actual response data is unavailable, call this:

```text
Modeled Air Advantage
```

not:
```text
Response-Time Improvement
```

---

# 24. SIGNATURE VISUAL: RESOURCE BACK IN SERVICE

Conceptual operational-capacity visual.

WITHOUT EARLY INTELLIGENCE:

```text
Incident A
Engine 1
Engine 2
Medic 1
Battalion

New Incident B
Available Units: 1
```

WITH EARLY SCENE INTELLIGENCE:

```text
Incident A
Engine 1
Medic 1

Engine 2 held/released

New Incident B
Available Units: 2
```

This is illustrative unless actual dispatch/cancellation data supports a historical example.

Clearly label illustrative scenarios.

---

# 25. MAP LAYERS

Fire mode may add:

- Fire Stations
- Neighboring / Mutual Aid Stations
- Drone Stations
- Ground Coverage Bands
- Drone Coverage Rings
- Calls by Fire Category
- Calls by Air Advantage
- Ground Coverage Gaps
- Drone-Covered Ground Gaps
- Remaining Gaps
- Hospitals
- High-Acuity EMS Calls
- WUI / Wildland Calls

Maintain current call/ring/station functionality.

---

# 26. EXECUTIVE KPIS

Candidate Fire KPIs:

- Total Calls
- Fire Calls
- EMS Calls
- ALS / High-Acuity Calls
- Calls Covered by Drone
- Ground Coverage Gap Calls
- Ground Gaps Covered by Drone
- Drone-First Opportunities
- Median Drone Lead Time
- Calls ≥60 sec Drone Lead
- Calls ≥120 sec Drone Lead
- Structure Fires Covered
- WUI Calls Covered
- High-Acuity Calls Covered
- Potential Apparatus Miles Avoided
- Potential Apparatus Hours Preserved
- Potential Crew Hours Preserved
- Modeled Annual Operating Impact

Only show metrics supported by current data/model.

---

# 27. HTML REPORT EXPORT

Existing HTML export must remain functional.

Fire-mode export should become an executive/customer report.

Suggested structure:

1. Executive Summary
2. Customer Operational Concern
3. 2025 Call Environment
4. Ground Response Coverage
5. Ground Coverage Gaps
6. Drone Coverage
7. Eyes Before Arrival
8. Two-Minute Opportunity
9. Fire / Thermal Intelligence
10. WUI / Wildland
11. Resource Right-Sizing
12. Financial / Capacity Impact
13. EMS / ALS
14. Hospitals / Community Context
15. Recommended Pilot Configuration
16. Methodology
17. Assumptions
18. Sources
19. Data Limitations

The export should preserve high-value map states as static snapshots where practical.

Animations do not need to survive export.

---

# 28. FIRE ASSUMPTIONS PANEL

Add configurable assumptions.

Possible fields:

```text
Drone launch delay (sec)
Drone cruise speed (mph)
Drone max radius (mi)
Minimum useful lead time (sec)
Ground turnout assumption (sec)
Ground modeled speed (mph)
Ground coverage target (min)
Apparatus operating rate
Mileage rate
Crew size
Modeled clear/downgrade rate
```

Each assumption should support:
- value
- unit
- source
- source year
- note

Avoid hidden assumptions.

---

# 29. SESSION MODEL

Fire-specific state should save inside `.tank` sessions where practical.

Examples:
- selected mode
- station roster
- hospital roster
- Fire classification settings
- drone assumptions
- ground assumptions
- financial assumptions
- presentation selections
- active map layers

Older sessions should still load gracefully.

---

# 30. FUTURE DATASETS

Fire mode should not be hard-coded to SRVFPD field names.

Create schema mapping / field detection for common equivalents.

Examples:

```text
incident_type
call_type
nature
problem
dispatch_type

latitude
lat
y

longitude
lon
lng
x

dispatch_time
time_dispatched
dispatch_datetime

arrival_time
first_arrival
onscene_time
```

Allow manual mapping when auto-detection is uncertain.

---

# 31. SAN RAMON PILOT

SRVFPD should be a configured session, not a separate product fork.

Primary station roster:
- Station 30
- Station 31
- Station 32
- Station 33
- Station 34
- Station 35
- Station 36
- Station 37
- Station 38
- Station 39

Use authoritative coordinates only.

Station 37 / Morgan Territory is an important analysis area due to ground-access considerations.

The provided 2025 call dataset may lack full response timestamps. If so:
- use modeled ground coverage
- do not claim actual 2025 response-time performance

---

# 32. FILE / MODULE ARCHITECTURE

Inspect the existing architecture before choosing exact filenames.

Preferred conceptual separation:

```text
js/
  fire/
    fire-mode.js
    fire-classifier.js
    fire-data-model.js
    fire-stations.js
    ground-coverage.js
    drone-response.js
    thermal-intelligence.js
    fire-resource-model.js
    fire-financial-model.js
    fire-ems-als.js
    fire-hospitals.js
    fire-presentation.js
    fire-report.js
```

Do not mechanically create all files if the current architecture suggests a cleaner organization.

The key requirement is modular isolation.

---

# 33. BACKWARDS COMPATIBILITY

Before implementation, establish baseline behavior for:

- General CAD load
- Demo data
- boundary detection
- calls map
- station creation
- optimizer
- station movement/editing
- filters
- coverage metrics
- station CSV export
- HTML report export
- `.tank` save/load

After every stage, retest these.

---

# 34. IMPLEMENTATION STAGES

Execute in order.

Do not implement all features in one uncontrolled pass.

---

# STAGE 0 — ARCHITECTURE AUDIT

## Objective

Understand the application before editing.

## Codex instructions

1. Inspect:
   - `index.html`
   - all files under `js/`
   - all CSS
   - assets relevant to map/report
2. Identify:
   - application startup
   - global state
   - CAD parsing pipeline
   - normalized call structure
   - station structure
   - map sources/layers
   - optimizer
   - response-time features
   - filters
   - report export
   - session save/load
3. Map dependencies.
4. Identify regression risks.
5. Recommend Fire module architecture.

## Deliverable

Return:
- architecture summary
- file responsibility map
- reusable components
- required modifications
- proposed new modules
- state changes
- backwards-compatibility plan
- test plan

## Rule

**DO NOT EDIT FILES IN STAGE 0.**

---

# STAGE 1 — FIRE MODE FOUNDATION

## Objective

Introduce Fire / EMS mode without changing General behavior.

## Build

- mode state:
  - General
  - Fire / EMS
- Fire mode selector
- Fire feature-gating
- Fire data model
- Fire call classifier
- call-category filters
- Fire-specific UI section container

## Requirements

- existing datasets behave exactly as before in General mode
- Fire mode may be manually selected
- optional Fire dataset detection may recommend mode, but must not force it
- retain original incident type

## Acceptance criteria

- General mode regression test passes
- Fire mode can classify calls
- no ground/drone financial logic yet

---

# STAGE 2 — FIRE STATIONS + GROUND COVERAGE

## Objective

Compare call demand to ground-station geography.

## Build

- Fire station CSV ingestion
- station source attribution
- official vs proposed station distinction
- nearest-station calculation
- modeled ground response
- configurable ground assumptions
- ground coverage bands
- ground coverage gap layer

## Acceptance criteria

For each eligible call:
- nearest station available
- ground distance available
- modeled ground timing available when possible
- coverage classification available

Clearly label modeled timing.

---

# STAGE 3 — DRONE RESPONSE + EYES BEFORE ARRIVAL

## Objective

Compare drone reach to ground coverage.

## Build

- drone launch assumptions
- drone flight model
- modeled drone arrival
- actual drone-vs-ground comparison when ground arrival timestamps exist
- modeled air advantage otherwise
- lead-time bands
- Eyes Before Arrival KPIs
- map coloring
- filters

## Acceptance criteria

Every displayed metric states whether it is:
- actual
- modeled

---

# STAGE 4 — THERMAL + FIRE / WUI INTELLIGENCE

## Objective

Add Fire-specific operational-awareness context.

## Build

- thermal capability layer
- visible/thermal presentation toggle
- structure-fire use-case panel
- WUI/wildland use-case panel
- rescue/search use-case panel
- thermal limitations disclosure
- call-category-specific thermal context

## Rule

Do not fabricate historical thermal observations.

---

# STAGE 5 — EMS / ALS + HOSPITALS

## Objective

Add high-acuity medical and community-response context.

## Build

- ALS/high-acuity classification
- EMS/ALS filters
- optional hospital data ingestion
- hospital map layer
- high-acuity coverage metrics
- ground/drone coverage comparison

## Rule

Do not claim lives saved.

Use:
- coverage
- access
- potential advance awareness
- response capacity

---

# STAGE 6 — RESOURCE RIGHT-SIZING

## Objective

Quantify resource opportunities where data supports it.

## Build

- unit/apparatus detection
- cancellation/downgrade indicators
- multi-unit response analysis
- potential right-sizing rules
- explicit actual vs modeled classification

## Graceful degradation

If unit-level data is absent:
- hide observed downgrade metrics
- allow scenario modeling only
- clearly label modeled scenario

---

# STAGE 7 — FINANCIAL + CAPACITY MODEL

## Objective

Translate right-sizing into defensible operational impact.

## Build

- apparatus miles
- apparatus hours
- crew hours
- equipment/mileage rate assumptions
- annual modeled operating impact
- capacity returned
- source/year fields
- report methodology output

## Rule

Avoid claiming all modeled impact is cash savings.

Use language such as:
- modeled operating impact
- utilization avoided
- resource capacity preserved
- apparatus-hours preserved

---

# STAGE 8 — CHIEF PRESENTATION MODE

## Objective

Create the strongest live demonstration.

## Build

### A. Executive opener
Large KPIs and customer problem.

### B. Annual call map
Interactive filters.

### C. Race to the Scene
Drone vs ground animation.

### D. Two-Minute Window
Timeline visualization.

### E. Ground Gap → Air Coverage
Coverage transformation.

### F. Thermal
Visible / thermal capability view.

### G. Resource Back in Service
Operational-capacity visualization.

### H. ALS
High-acuity scene-awareness view.

### I. Executive summary
Eyes First / Capacity / Operating Impact / High-Acuity Coverage.

## Requirements

- data-driven
- minimal controls
- presentation-safe
- explicit actual vs modeled labels
- analyst mode remains available

---

# STAGE 9 — FIRE HTML REPORT EXPORT

## Objective

Turn analysis into a polished customer deliverable.

## Build

Fire report sections listed earlier.

Requirements:
- executive summary
- customer problem
- source labels
- methodology
- assumptions
- limitations
- static map/report visuals
- annual KPIs
- no unsupported conclusions

Preserve current General report behavior.

---

# STAGE 10 — SESSION + SAN RAMON PILOT

## Objective

Create reusable Fire session support and validate SRVFPD.

## Build / Verify

- Fire state saved to `.tank`
- station roster persisted
- assumptions persisted
- presentation mode state where appropriate
- old session compatibility
- SRVFPD session configuration

## Suggested output

```text
SRVFPD_2025_Fire_Chief.tank
```

Do not hard-code San Ramon logic into generic modules.

---

# STAGE 11 — QUALITY / REGRESSION PASS

## Objective

Stabilize the entire application.

Test:

### General Mode
- CAD load
- demo
- filters
- map
- optimizer
- manual stations
- exports
- sessions

### Fire Mode
- sparse dataset
- rich timestamp dataset
- unit-level dataset
- missing coordinates
- missing response times
- missing unit data
- station CSV
- hospital CSV
- report
- presentation
- sessions

Check:
- console errors
- map layer conflicts
- memory growth
- duplicate event handlers
- repeated module initialization
- stale UI state
- session migration issues
- report failures

---

# 35. CODING REQUIREMENTS

- Prefer pure functions for calculations.
- Avoid hidden global state where practical.
- Document units:
  - seconds
  - minutes
  - miles
  - mph
  - dollars/hour
  - dollars/mile
- Centralize Fire assumptions.
- Do not duplicate calculation logic between UI and export.
- Export should consume the same computed Fire analysis state as the live application.
- Avoid expensive all-call recomputation on every minor UI event when caching is reasonable.
- Keep presentation animation logic separate from analytical calculations.

---

# 36. MODEL TRANSPARENCY

Every modeled metric shown to a user should be traceable.

Example detail panel:

```text
Modeled Drone Arrival
Launch delay: 30 sec
Distance: 2.7 mi
Cruise speed: 50 mph
Flight time: 3:14
Total modeled arrival: 3:44
```

Example ground model:

```text
Modeled Ground Arrival
Nearest station: Station 34
Distance: 3.9 mi
Turnout assumption: 60 sec
Travel model: 35 mph
Total modeled arrival: 7:41
```

This transparency is important for Fire Chief credibility.

---

# 37. DATA LIMITATION BEHAVIOR

Never fail silently.

Examples:

```text
Actual first-arrival timestamp unavailable.
Showing modeled ground response.
```

```text
Unit-level dispatch data unavailable.
Resource right-sizing shown as scenario analysis only.
```

```text
Station coordinates unavailable.
This station is excluded from spatial timing analysis until geocoded.
```

---

# 38. FIRE PRESENTATION LANGUAGE

Preferred terms:

- Eyes Before Arrival
- Advance Scene Awareness
- Live Scene Intelligence
- Ground Coverage Gap
- Modeled Air Advantage
- Resource Capacity Preserved
- Potential Right-Sizing Opportunity
- Modeled Operating Impact
- High-Acuity Coverage

Avoid unsupported language:

- Guaranteed lives saved
- Guaranteed cost savings
- Actual response improvement when based on modeled data
- Confirmed downgrade when based on inference
- Thermal sees through walls

---

# 39. CODEX OPERATING PROMPT

After placing this file in the repository root, give Codex this single prompt:

```text
Read FIRE_INTELLIGENCE_MASTER_PLAN.md in full.

Treat it as the authoritative product and implementation specification for the Fire / EMS Intelligence work.

Start with STAGE 0 only.

Inspect the complete repository and produce the Stage 0 architecture audit requested by the document.

Do not modify any files yet.

Your Stage 0 response must include:
1. architecture map
2. relevant files and responsibilities
3. reusable functions/modules
4. coupling and regression risks
5. proposed Fire architecture
6. exact files likely to change
7. proposed new files/modules
8. state/data-model changes
9. backwards-compatibility strategy
10. test strategy
11. any conflicts between the current codebase and the master plan

Stop after Stage 0 and wait for approval before editing.
```

---

# 40. PROMPT TO BEGIN EACH IMPLEMENTATION STAGE

After reviewing Stage 0:

```text
Read FIRE_INTELLIGENCE_MASTER_PLAN.md again.

Implement STAGE [NUMBER] only.

Before editing:
- restate the Stage objective
- list the files you expect to change
- identify General-mode regression risks

Then implement the stage.

After implementation:
- summarize changes
- list files changed
- report tests/checks performed
- report General-mode regression results
- report Fire-mode validation results
- report known limitations
- do not begin the next stage
```

Replace `[NUMBER]` with the desired stage.

---

# 41. FINAL PRODUCT PRINCIPLE

JavaFrank should feel custom to a Fire Chief without becoming a custom one-off application.

The final experience should communicate:

> The value is not simply how fast the drone flies.
> The value is what the department can know before its people arrive.

Use:
- local call data
- local stations
- ground coverage
- aerial coverage
- live video
- thermal
- resource capacity
- Fire / EMS operational context

while preserving the complete General public-safety analysis workflow.
