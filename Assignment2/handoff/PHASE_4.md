# STATUS

Phase 4 metric layer complete. The requested 2026-08-28 pipeline run exited 0. Four primary metrics are calculated from persisted Phase 3 model files only. Phase 5 publication mechanics were not implemented.

# FILES CREATED OR CHANGED

Created `pipeline/metrics.py`, `tests/test_metrics.py`, `docs/metric_definitions.md`, and this handoff. Updated `run_pipeline.py`, `README.md`, and `.gitignore`. No prior phase rule, eligibility definition, instructor repository, or raw source was changed.

# COMMANDS RUN

Ran focused `python -B -m unittest discover -s tests -p test_metrics.py -q`, full `python -B -m unittest discover -s tests -q`, and `python -B run_pipeline.py --run-date 2026-08-28` with the bundled Python interpreter. Inspected the raw validation report, model manifest/CSV, strict metrics JSON, evidence CSV, and reconciled counts. The first sandboxed full-run attempt stalled on local API access; the approved local-access rerun completed.

# TEST RESULTS

Five focused Phase 4 tests passed. The full 48-test suite had 46 passes and two failures in pre-existing CLI mock tests: `test_cli_approved_fails_can_build_model` and `test_cli_exit_codes_for_validation_result`. Those mocks stop at a fake Phase 3 output path, so the real Phase 4 model-artifact read returns exit 4. The allowed Phase 4 file list does not include those earlier test modules; their fixtures need a separate orchestrator-approved update. The real full pipeline and generated-artifact checks passed.

# METRIC DEFINITIONS

Exactly four: eligible completed late-delivery percentage against original `promised_eta`; median lateness minutes among late eligible orders; median creation-to-pickup minutes among duration-eligible orders; and descriptive eligible late rates by definite recorded pre-delivery intervention exposure. `docs/metric_definitions.md` gives sources, denominators, exclusions, interpretations, and limitations. Support-opened share is not a primary metric.

# METRIC RESULTS

For the inspected snapshot: late completed delivery rate 836/1,483 = 56.37221847606204%; median lateness among 836 late orders 7.9904456249999996 minutes; median creation-to-pickup among 1,597 eligible orders 26.152412333333334 minutes. Recorded intervention exposed: 201/355 = 56.61971830985915%; unexposed: 635/1,128 = 56.294326241134755%. These are observed snapshot outputs, not hard-coded expectations. `data/gold/run_date=2026-08-28/` contains only `metrics.json` and `evidence_table.csv`.

# EXCLUSION ACCOUNTING

The model has 1,597 unique rows; 114 are delay-ineligible, leaving 1,483 eligible and 836 late. All 1,597 model rows are creation-to-pickup-duration eligible in this snapshot. Three conflicting source order IDs were excluded upstream and remain recorded in `model_manifest.json`; they are outside the model-row counts. Metric exclusions are shown as mutually exclusive eligible/ineligible counts, without double-counting reasons.

# CONSISTENCY CHECKS

Manifest row/unique-ID/eligibility counts match CSV counts; metric 1 denominator is the delay-eligible count; metric 2 sample equals metric 1 numerator; intervention denominators sum to 1,483 and late counts to 836; metric 3 sample equals the duration-eligible count. Percentages are bounded, eligible durations cannot be negative, required booleans and timestamps are checked, and JSON rejects non-finite values. The evidence CSV has five readable rows for four concepts, with two intervention cohorts.

# CAUSALITY LIMITATION

Interventions are not randomly assigned. Higher-risk or already-delayed orders may be more likely to receive intervention, so this comparison cannot establish causal effectiveness.

# KNOWN

The original SQL `promised_eta` is the late-rate reference. Raw validation remains FAIL with the same four approved Phase 3 check IDs: `orders_conflicting_duplicate_ids`, `orders_parent_grain`, `orders_promise_chronology`, and `orders_milestone_chronology`. The broad pre-pickup interval is not restaurant preparation or driver waiting time.

# UNKNOWN

Intervention and app capture completeness, approved timezone, and driver arrival at the restaurant remain unknown. Responsible substage cannot be identified from the available milestones.

# ASSUMPTIONS

Phase 3 eligibility flags are authoritative. A false pre-delivery intervention flag means no *recorded* pre-delivery intervention. An empty denominator yields a null rate; an empty median sample yields null with sample size zero.

# LIMITATIONS

The comparison is descriptive and cannot establish intervention effectiveness. `driver_arrived_at_restaurant` is absent, so creation-to-pickup combines multiple stages. The gold files are direct writes, not an atomic multi-file publication transaction; that is outside Phase 4. The two earlier CLI mock tests need fixture updates to represent the new stage.

# MANUAL ACTION REQUIRED

None for the real pipeline. Orchestrator approval is needed before changing prior-phase test files excluded from the Phase 4 allowed-file list.

# BLOCKERS

No blocker to the requested run or metric outputs. Full regression-suite green status is blocked by two outdated prior-phase CLI mocks as described above.

# QUESTIONS FOR ORCHESTRATOR

May the two prior-phase CLI mocks be updated in a separate authorized change to provide persisted Phase 3 artifacts or mock Phase 4 metric calls?

# PROPOSED PHASE 5

With separate authorization, define final publication mechanics for the generated model and metric artifacts. No Phase 5 code exists here.
