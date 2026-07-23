# Automatic Guardian Land-Coverage Optimization — Design

## Problem

When a stations file and calls file are uploaded, the user wants Guardian
stations selected for maximum geographic land coverage. The current uploaded
station cards are primarily a display-and-manual-selection workflow, and
their role-dependent sorting does not provide an automatic land-coverage
deployment plan. Re-enabling the former fleet sliders would risk coupling
widget counts, card state, map state, and deployed-unit state again.

The York County test data contains 28 uploaded station candidates and 1,855
call records. Calls remain useful for context and reporting, but they are not
the primary objective of this workflow.

## Goal

Add an automatic Guardian-only optimization mode that:

1. Starts with no selected Guardian stations.
2. Adds the remaining station that contributes the most previously uncovered
   land.
3. Recomputes the union of selected Guardian coverage areas after every pick.
4. Stops when no remaining candidate adds measurable new land.
5. Reflects the selected stations in the existing cards, map, counts, and
   deployment records without changing station identity or card order.

“Measurable value” means positive new area after the geometry's numerical
tolerance is applied. A station contributing only negligible overlap is not
selected.

## Recommended approach

Reuse the existing greedy area-coverage mechanism, but make this workflow
explicitly Guardian-specific. It is fast for uploaded candidate sets,
explainable to users, and already matches the application's coverage-union
model. A full integer-programming model would require an arbitrary penalty or
budget to decide how many stations to use; selecting every station would add
redundant deployments.

The optimizer is greedy rather than mathematically guaranteed to find the
global best subset. Its selection order and marginal gains are transparent,
which is more useful here than an opaque solution with an invented station
cost.

## Coverage calculation

- Guardian land selection must use each station's `clipped_guard` geometry.
- The selected-area metric is the union of all selected Guardian geometries
  intersected with the active jurisdiction boundary.
- Candidate gain is:

  `area(union(current_selection + candidate)) - area(union(current_selection))`

- Candidate selection is deterministic: larger marginal gain wins; ties use
  stable station index/order.
- The algorithm never uses call count as the primary selection score.
- Guardian call percentages may continue to be shown as supporting metrics.

## User workflow

In the uploaded-stations flow, provide a clear action such as “Optimize
Guardian Land Coverage.” The action runs the automatic selection across the
uploaded candidates and updates the existing deployment state.

The UI reports:

- number of selected Guardian stations;
- total land covered and coverage percentage;
- each selected station's marginal land contribution;
- the station names selected on the cards and map.

There is no required Guardian-count slider for this mode. The optimizer
determines the count by the measurable-value stopping rule, bounded by the
number of uploaded candidates.

## State and synchronization

The optimizer must use the existing stable station identity (`station_idx`
and current station identity keys). It must not infer identity from display
rank or card position.

After optimization:

- selected candidates have mode `Guardian`;
- unselected candidates remain `Off` unless the user has a later manual role
  selection;
- Guardian count equals the number of active Guardian deployments;
- active card identities and deployed-unit identities match exactly;
- no station is simultaneously Guardian and Responder;
- map rings and station markers use the same selected identities.

Manual card changes remain authoritative after the automatic run. Selecting a
station manually deploys that exact station and must not silently substitute a
different station because of rank, overlap, or optimizer output. A later
explicit optimizer action may replace the automatic plan, but that replacement
must be visible and deterministic.

Card order remains stable. Optimization changes card mode and deployment state,
not the station's identity-bearing sort position.

## Error handling

- If no station candidates exist, show the existing station-candidate error
  and do not mutate deployment state.
- If the jurisdiction area is unavailable or invalid, do not claim a land
  percentage; show the available station-level state and an explanatory error.
- Empty or invalid station geometries contribute zero gain and are skipped.
- Repeated runs with unchanged uploaded data produce the same selected station
  identities and order.

## Scope

In scope:

- uploaded stations-file workflow;
- automatic Guardian land-coverage selection;
- Guardian-specific geometry and marginal-gain stopping;
- synchronization with existing cards, map, counts, and deployments;
- focused unit tests and a live UI smoke test.

Out of scope:

- redesigning the existing manual card controls;
- changing Responder call-coverage optimization;
- changing the no-upload candidate-generation workflow;
- adding an arbitrary budget or station-cost model;
- unrelated generated files or deployment changes.

## Expected implementation files

- `modules/dashboard_helpers.py` — orchestration, suggestion/card state, and
  rendering of the automatic Guardian action and metrics.
- `modules/optimization.py` — reusable Guardian land marginal-gain selection
  helper, if the existing helper cannot be safely parameterized.
- `app.py` — wire the uploaded-flow action into the active optimization and
  deployment state.
- `tests/` — focused optimizer and synchronization coverage.

## Validation criteria

Automated tests must verify:

- Guardian geometry is used rather than Responder geometry;
- marginal gains are non-increasing or correctly recomputed from the current
  union;
- zero/negligible-gain candidates are excluded;
- stable tie-breaking and repeatability;
- exact card/deployment identity equality;
- no duplicate Guardian/Responder station identity.

A live Streamlit smoke test must upload or load the York County files and
verify the visible selected count, card roles, map/ring state, land-coverage
metric, and deployed station names agree after the optimizer action and a
rerun.
