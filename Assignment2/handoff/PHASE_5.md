# STATUS

Phase 5 staged publication and run diagnostics are complete. The full test suite passes, and two real same-date runs completed with exit 0. Phase 6 was not implemented.

# FILES CREATED OR CHANGED

Created `pipeline/publish.py`, `pipeline/logging_config.py`, `tests/test_publish.py`, `tests/test_pipeline_e2e.py`, `docs/pipeline_operations.md`, and this handoff. Updated `run_pipeline.py`, minimally logged API retries/source counts in `pipeline/extract.py`, and updated `README.md` and `.gitignore`. With explicit follow-up authorization, updated the prior CLI mocks in `tests/test_validate.py` and `tests/test_transform.py` for the publication boundary. No metric, eligibility, or validation rule changed.

# COMMANDS RUN

Ran focused publication/e2e tests and `python -B -m unittest discover -s tests -q`; ran `python -B run_pipeline.py --run-date 2026-08-28` twice after implementation. Compared the six published hashes, run manifests, logs, raw FAIL IDs, page count, model uniqueness, metric values and evidence row count. Controlled synthetic failures ran against temporary directories in the tests.

# TEST RESULTS

53 tests passed with no failures or skips. Synthetic tests cover replacement, rollback, last-success preservation after validation/model/metric failures, deterministic reruns, logging, hashes, strict JSON, unique model grain, four primary metrics, five evidence rows, and no stale API page append. Both real reruns exited 0. The final observed values equal Phase 4: late rate 56.37221847606204%; median late minutes 7.9904456249999996; median creation-to-pickup minutes 26.152412333333334. No production business value changed.

# RUN ID

Each invocation gets a UTC timestamp plus short random suffix. The two verified attempts had distinct IDs `20260927T175908399664Z-0aceb905` and `20260927T180008286382Z-c801b275`. Run ID labels attempt state only; logical `run_date` remains `2026-08-28` for both.

# LOGGING

Each attempt writes `data/.runs/<run_id>/logs/pipeline.log` with run ID/date, stage transitions, source counts, API retries, validation summary and handled/unhandled FAILs, model rows/exclusions, metric IDs, publication actions, and failure messages. Both real logs exist. Console output remains concise.

# STAGE PUBLICATION

Extract, validation, model and metrics build under the unique attempt workspace. Before publishing, six files and their consistency contracts are checked. The three complete `run_date` directories replace their prior versions using sibling backups; any publication failure rolls replacements back. Latest success metadata is written only after all three are published and verified. No incomplete staged file is exposed as a final artifact.

# FAILURE PRESERVATION

Failed attempts retain their attempt manifest, log and any staged artifacts. Synthetic validation, model and metric failures left the prior published gold bytes and latest successful manifest intact. Injected gold-directory rename failure restored all prior public directories and kept the old latest manifest.

# RERUN CHECK

The two real same-date runs produced identical SHA-256 hashes for all six business artifacts and different run IDs. Each published raw directory had exactly eight API pages; the model had 1,597 rows and 1,597 unique IDs; gold had exactly four primary definitions and five evidence rows. The second run became `data/run_manifest.json`.

# FINAL RUN MANIFEST

Each attempt has strict `run_manifest.json` recording run ID/date, start/end, status, exit code, five stage statuses/times/messages, project-relative artifact paths, validation/model summaries, handled FAIL IDs, warning/unknown counts, metric IDs and Python version. `data/run_manifest.json` reflects only the latest fully successful run.

# ARTIFACT HASHES

The latest manifest records SHA-256 for raw manifest, validation report, order journey CSV, model manifest, metrics JSON and evidence CSV. All six recorded hashes matched the published bytes; both real runs produced the same six hashes.

# EXIT CODES

`0` success; `1` configuration/extraction/validation runtime; `2` unhandled validation FAIL; `3` model failure; `4` metric failure; `5` publication/finalization failure.

# KNOWN

The raw validation report still has the four approved FAIL IDs (`orders_conflicting_duplicate_ids`, `orders_parent_grain`, `orders_promise_chronology`, `orders_milestone_chronology`). Bounded API retry semantics and all four Phase 4 metric definitions remain unchanged.

# UNKNOWN

Source timezone, intervention/app capture completeness, and restaurant-arrival milestone remain unresolved business-data limits.

# ASSUMPTIONS

The attempt and public data roots share a local filesystem that supports sibling directory rename. Only one writer publishes a given logical date at a time.

# LIMITATIONS

Local rollback is not a cross-filesystem or concurrent-writer transaction. Automatic attempt retention windows and operational cleanup are outside assignment scope. Successful attempts keep logs/manifest, while their staged data directories have moved to public locations.

# MANUAL ACTION REQUIRED

None for the demonstrated local run.

# BLOCKERS

None for Phase 5.

# QUESTIONS FOR ORCHESTRATOR

None required for Phase 5 completion.

# PROPOSED PHASE 6

With separate authorization, prepare submission/demo documentation around the existing reproducible command, artifacts, limitations and proof of validation. No Phase 6 work was included here.
