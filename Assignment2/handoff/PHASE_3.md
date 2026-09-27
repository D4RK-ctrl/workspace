# STATUS

Phase 3 workflow model complete; awaiting orchestrator review. The real raw validation report remains FAIL, with only the four approved, explicitly modelled quality failures allowed to proceed. No KPI metrics or later publication stage was implemented.

# FILES CREATED OR CHANGED

Created `pipeline/clean.py`, `pipeline/transform.py`, `tests/test_clean.py`, `tests/test_transform.py`, `docs/workflow_model.md`, and this handoff. Updated `run_pipeline.py`, `README.md`, and `.gitignore`. Made a minimal update to the existing Phase 2 CLI mock in `tests/test_validate.py` because Phase 3 now requires check IDs in the report. No Phase 2 validation rule was weakened.

# COMMANDS RUN

Read the Phase 2 handoff, validation contract and current pipeline files; ran focused synthetic unit tests with `python -B -m unittest discover -s tests -q`; ran `python -B run_pipeline.py --run-date 2026-08-28`; inspected the raw validation report, generated CSV and strict JSON model manifest, unique IDs, exclusions, join checks, file scope and instructor-repository status. The final full run was repeated after the modelling-readiness guard moved into the model builder. Generated run-directory access required sandbox escalation.

# TEST RESULTS

43 tests passed, including Phase 1/2 regression tests and Phase 3 synthetic cases for duplicate classification, eligibility, normalization/provenance, child aggregation, timing, dispatch driver separation, fan-out prevention, readiness whitelist and strict output. A non-failing socket ResourceWarning from the existing local HTTP test appeared in the combined suite.

# MODEL GRAIN

One output row equals one included canonical order. `order_journey.csv` has 1,597 rows and 1,597 unique `order_id` values in the inspected snapshot. The output has 52 fields covering entities, lifecycle, states, interactions, interventions, dispatch and eligibility. No final KPI values are present.

# ORDER CONFLICT HANDLING

Input has 1,603 order rows / 1,600 distinct IDs. Three conflicting IDs (`O00120`, `O00723`, `O01302`) are excluded entirely and listed in `model_manifest.json` with `model_excluded: true` and reason `conflicting_order_versions`. No first-row winner was chosen. The current snapshot has no exact full-row duplicates; synthetic tests confirm identical duplicates collapse with source-row provenance.

# ELIGIBILITY RULES

`chronology_valid` checks observed parseable creation, pickup and completion order plus promise versus creation; missing completion alone does not invalidate chronology. `delay_metric_eligible` requires delivered status, parseable promise/completion and valid chronology. `duration_metric_eligible` requires a parseable, ordered creation-to-pickup interval; this flag is specific to that interval. The snapshot has 9 chronology-invalid included orders, 1,483 delay-eligible orders and 1,597 creation-to-pickup-duration-eligible orders. These are row counts/flags, not rates or published metrics. Missing SQL completion remains null; dispatch never fills it or replaces `promised_eta`.

# CHILD AGGREGATION

2,365 app-action rows reduced to 1,100 order aggregates; four actions link to excluded parent IDs and are counted as not joined. 430 intervention rows reduced to 430 order aggregates. Type counts are distinct, total/pre/post/unclassified timing is separate, and `has_pre_delivery_intervention` requires observed timing within creation and completion. When completion is absent, interventions are unclassified rather than labelled rescues. Zero joined counts mean no recorded child row; capture completeness is unknown.

# FAN-OUT CHECKS

App actions, interventions and dispatch each passed a unique child-order-ID check before its left join. After each join, parent rows and unique IDs remained 1,597; the manifest records all three checks. A duplicate dispatch ID or any child aggregate duplication raises a model error; an unhandled validation FAIL returns exit code 2 before model construction.

# MODEL RESULTS

`data/processed/run_date=2026-08-28/` contains only `order_journey.csv` and strict `model_manifest.json`. The final command returned exit code 0. `data/raw/run_date=2026-08-28/validation_report.json` still reports 54 PASS, 8 WARN, 4 FAIL and 4 UNKNOWN, overall FAIL. The four FAIL check IDs are `orders_conflicting_duplicate_ids`, `orders_parent_grain`, `orders_promise_chronology`, and `orders_milestone_chronology`; no other FAIL was ignored.

# KNOWN

`sql_driver_id`, `dispatch_driver_id` and `dispatch_original_driver_id` remain separate. Raw and normalized status/traffic/weather fields coexist. `driver_assignment_changed` compares dispatch original versus current only when both are known. Intervention comparisons remain descriptive.

# UNKNOWN

Customer action/intervention capture completeness, approved source timezone, production freshness SLA and observed restaurant-arrival milestone remain unresolved. No restaurant-versus-driver stage attribution is possible.

# ASSUMPTIONS

Trim/lowercase is representation-only normalization for order status, traffic and weather; child action/intervention categories retain source values. A duration flag refers only to the creation-to-pickup interval. An unclassified child time is not silently assigned to an in-flight cohort.

# LIMITATIONS

The model is an analytical preparation artifact, not an approved KPI publication. Child rows for excluded parents remain in raw evidence and are summarized as not joined. Same-date processed output is replaced after construction but is not a multi-file publication transaction. Phase 2 raw FAIL status remains visible and must be considered before later metrics.

# MANUAL ACTION REQUIRED

None to reproduce Phase 3 beyond the documented Python setup and command.

# BLOCKERS

No implementation blocker. The observed raw FAILs are narrowly handled for this model only; KPI definitions and publication remain outside Phase 3.

# QUESTIONS FOR ORCHESTRATOR

Confirm the future eligible population, approved timezone, source-capture expectations and how the excluded conflicting IDs should affect downstream denominators. Decide whether duration eligibility should remain interval-specific as documented before Phase 4 metrics are authorized.

# PROPOSED PHASE 4

Only with separate approval, define and calculate a small KPI set from explicitly eligible model rows, retaining denominators/exclusions and the raw validation caveats. No Phase 4 code exists in this commit.
