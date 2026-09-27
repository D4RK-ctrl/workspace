# STATUS

Phase 1 extraction complete. No cleaning, validation gates, order journey, or metrics implemented. Awaiting orchestrator review.

# FILES CREATED OR CHANGED

Created `Assignment2/README.md`, `requirements.txt`, `.gitignore`, `.env.example`, `run_pipeline.py`, `pipeline/__init__.py`, `pipeline/config.py`, `pipeline/extract.py`, `tests/test_extract.py`, and this handoff. Added only approved fixtures under `Assignment2/data/source/`. Phase 0 documents and instructor repositories are unchanged. Generated `data/raw/` is ignored.

# SOURCE FILES COPIED

- `database/flasheats.db` -> `data/source/database/flasheats.db` (SHA-256 matched)
- `data/customer_app_actions.csv` -> `data/source/files/customer_app_actions.csv` (SHA-256 matched)
- `data/order_interventions.csv` -> `data/source/files/order_interventions.csv` (SHA-256 matched)
- `api/mock_dispatch_api.py` -> `data/source/api/mock_dispatch_api.py` (SHA-256 matched)
- `api/dispatch_data.json` -> `data/source/api/dispatch_data.json` (SHA-256 matched; fixture backing the HTTP service, not an extraction result)

# COMMANDS RUN

Inspected relevant paths and the copied API source; installed the declared Flask dependency because the active bundled Python lacked it; ran `python -B -m unittest discover -s tests -v`; ran `python -B run_pipeline.py --run-date 2026-08-28` twice using the bundled Python; checked manifest/artifact hashes, source copies, Git scope, and reference-repository status. Initial dependency install was blocked by sandbox network access and succeeded after approved escalation. Generated raw-directory access also required sandbox escalation.

# TEST RESULTS

Six focused `unittest` tests passed after correcting SQLite connection lifetime in the extractor and test setup. They cover exact CSV copy, dynamic SQL schema/row retrieval, multi-page API retrieval, retry after transient 500, immediate failure on permanent 404, and same-date replacement of stale API pages. The Phase 1 command succeeded twice. The first full-run SQL artifact used CSV before the explicit NULL-preserving JSON Lines correction; final tests and both recorded full runs use JSON Lines.

# EXTRACTION RESULTS

For the supplied snapshot: orders 1,603 rows; customer app actions 2,365 rows; interventions 430 rows; dispatch 1,600 records over 8 pages. These are observations in the manifest, not code assertions or final metrics. SQL is opened read-only, CSV bytes are copied, and dispatch records come through HTTP only.

# API RETRY AND PAGINATION EVIDENCE

The bundled mock API was started and stopped by each run. Both full runs logged one HTTP 500 retry on page 3 and one HTTP 429 retry on page 5; the latter respected the fixture's one-second retry hint. Pages 1 through 8 were retrieved. Manifest evidence records page progression, `has_more` termination, a consistent reported total, 1,600 received records and 1,600 unique order IDs. Tests also verify transient retry and no retry for HTTP 404.

# RAW ARTIFACTS

`Assignment2/data/raw/run_date=2026-08-28/` contains `sql/orders.jsonl`, exact copied CSVs under `files/`, `api/page_0001.json` through `page_0008.json`, and strict `manifest.json`. SQL JSON Lines preserves the distinction between SQLite NULL and empty text. API page bodies are saved before page contents are interpreted or counted. The manifest has four source entries with mode, location, count, columns, artifact and completeness status; API details include pages, total and unique IDs.

# IDEMPOTENCY CHECK

Two final same-date runs succeeded. Each produced exactly 12 raw files, with identical relative paths and SHA-256 hashes; there were no extra or appended API pages. A focused test also shortened a mock API result from two pages to one on rerun and confirmed the stale page disappeared.

# KNOWN

The copied mock API requires Flask. The local endpoint starts automatically when absent; an already healthy compatible endpoint is reused. The command exits nonzero on extraction/configuration failure. Source fixtures are in the student project, so the ignored instructor repositories are unnecessary at runtime.

# UNKNOWN

Business source authority, real API SLA, timestamp semantics and downstream eligibility remain Phase 0 questions. This phase does not resolve them.

# ASSUMPTIONS

The bundled API fixture implements the inspected classroom contract: `/health`, `/dispatch/orders`, `page`, `page_size`, `has_more`, `total_records` and `data`. The maximum requested page size is 200, matching its cap. The logical run date identifies raw output; it is not an event-date filter.

# LIMITATIONS

Same-date publication replaces a completed raw directory after successful extraction but is not a multi-file transaction. Prior output remains if retrieval fails before replacement. Automatic mock startup is limited to the configured default local port 8000; custom endpoints must already be healthy. No cleaning, lifecycle checks, cross-source reconciliation or business metrics are present.

# MANUAL ACTION REQUIRED

None for the committed clean-clone path beyond installing `requirements.txt` and running the documented command. The execution environment used a bundled Python because `python` was absent from its PATH.

# BLOCKERS

None for Phase 1 completion.

# QUESTIONS FOR ORCHESTRATOR

Review the raw source/manifest contract and Phase 0 business decisions before authorizing Phase 2. Confirm whether a future phase needs a stronger publication transaction or different source freshness policy.

# PROPOSED PHASE 2

With separate authorization, define business validation rules, source conflict handling and eligibility. Do not derive order journeys or metrics until their contracts are approved.
