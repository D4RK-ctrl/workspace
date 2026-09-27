# STATUS

Final submission documentation is complete. No production logic, source fixture, test, validation, model-eligibility or metric definition changed. Awaiting final orchestrator review.

# FILES CREATED OR CHANGED

Created `docs/submission_summary.md`, `docs/source_map.md`, `docs/demo_script.md`, `docs/decision_output.md` and this handoff. Rewrote `README.md` for the final submission. Corrected stale historical paths/wording only in `docs/source_audit.md` and `docs/proposed_architecture.md`. Phase 0–5 handoffs remain unchanged.

# COMMANDS RUN

Ran `python -B -m unittest discover -s tests -q`, then `python -B run_pipeline.py --run-date 2026-08-28`. Inspected the latest run, raw validation, model and gold manifests/CSV, portable paths and hashes. Checked Git-tracked source fixtures, ignored generated paths, current documentation for stale strings, and remote/branch. Copied 45 Git-indexed Assignment2 files into a fresh temporary directory without `reference/`, then ran the command and full tests there.

# FINAL TEST RESULT

Local full suite: **53 tests, 0 failures, 0 skips**. Temporary clean-copy full suite: **53 tests, 0 failures, 0 skips**. The local and clean-copy pipeline commands both exited 0. No tests were changed in Phase 6.

# CLEAN CLONE CHECK

The fresh indexed-file copy contained the tracked SQLite, CSV and local API fixtures and no instructor repositories. Existing Flask 3.1.3 satisfied `requirements.txt` (`Flask>=3.0,<4`). Its one-command run produced a successful manifest with six relative, hash-matching artifact locations and exactly four primary metrics. The full suite passed there.

# FINAL REPOSITORY STRUCTURE

`Assignment2/` contains `README.md`, `requirements.txt`, `.env.example`, `run_pipeline.py`, `pipeline/`, `tests/`, `docs/`, `handoff/`, and tracked `data/source/`. Generated `data/raw/`, `data/processed/`, `data/gold/`, `data/.runs/` and `data/run_manifest.json` are ignored and untracked. Root `reference/` retains the PDF and lecture context; both local instructor repositories are ignored.

# SUBMISSION REQUIREMENTS CHECK

The README covers problem, stakeholders, primary KPI, four runtime sources, retrieval modes, architecture, source map, quality gates, model, four metrics, findings, decision, Known/Unknown/Assumption/Limitation, setup, one-command run, outputs, exit codes, tests, structure and demo. Separate source map, rubric summary, business decision output and ~4-minute demo script exist. No notebook, dashboard, model, cloud or manual API startup is needed. The latest successful manifest uses project-relative locations and matching hashes; raw validation evidence remains visible.

# FINAL BUSINESS FINDINGS

Observed on the supplied classroom snapshot for logical date 2026-08-28: eligible late completed-delivery rate **56.37%** (836/1,483); median lateness among late eligible orders **7.99 minutes**; median creation-to-pickup **26.15 minutes**. Descriptive late rates are **56.62%** for orders with a recorded pre-delivery intervention and **56.29%** otherwise. These are observations from `metrics.json`, not test constants or causal effects.

# IMPORTANT FDE JUDGMENT CALL

`driver_arrived_at_restaurant` is not observed. The broad pre-pickup interval cannot defensibly separate restaurant preparation from driver travel or waiting, so no stage blame is assigned. The original SQL promise anchors lateness; conflicting parents are excluded without arbitrary selection; invalid chronology affects eligibility; missing completion is not filled; child aggregation prevents fan-out; and intervention comparisons stay descriptive.

# KNOWN

Four canonical runtime sources, one-row-per-included-order model, original-promise KPI and four approved primary metrics. The raw report still records four handled FAIL IDs. The final local run exited 0; the model manifest reports 1,597 rows and 1,597 unique IDs; gold has four primary definitions and five evidence rows.

# UNKNOWN

Approved source timezone, event-capture completeness, production freshness SLA, observed restaurant arrival and causal intervention effect remain unknown.

# ASSUMPTIONS

Trim/lowercase changes representation only; logical run date partitions output; absent recorded child events do not prove complete capture; local publication assumes one writer on a shared filesystem.

# LIMITATIONS

Conflicting parent IDs are outside the model; impossible chronology and missing completion restrict measurable cohorts. Restaurant-versus-driver attribution and causal intervention effectiveness are unsupported. Local rollback is not a distributed transaction.

# MANUAL ACTION REQUIRED

After reviewing this commit, push `main` to `origin` and submit the Assignment2 URL. The local commit alone does not publish it to GitHub.

# BLOCKERS

None for the local submission artifact or clean-clone run.

# FINAL SUBMISSION URL

https://github.com/D4RK-ctrl/workspace/tree/main/Assignment2

# DEMO SCRIPT

[docs/demo_script.md](../docs/demo_script.md) provides a four-minute walkthrough and ten concise viva answers.
