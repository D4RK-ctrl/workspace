# FlashEats pipeline operations

## Run command

From `Assignment2/`, install the existing requirements and run `python run_pipeline.py --run-date YYYY-MM-DD`. The date is a logical business run date, not the execution timestamp.

## Stage sequence

Extract, Validate, Model, Metrics, then Publish. Every stage builds under a fresh attempt directory. The complete raw, processed, and gold directories are checked before publication.

## Run ID vs run date

Each invocation receives a UTC timestamp plus random suffix in its `run_id`. The ID labels logs and attempt metadata; all business artifacts remain partitioned by the requested `run_date` and do not use `run_id` in calculations.

## Retry behavior

The dispatch API keeps bounded retries for HTTP 429, 500, 502, 503, 504 and network errors, including bounded wait times. Ordinary permanent 4xx responses fail immediately. Retry events appear in the attempt log and concise console output.

## Validation blocking rules

The Phase 2 report preserves every raw check result. Only the four approved Phase 3 modelling exceptions can proceed; any other FAIL exits 2 before modelling or publication. A failed validation attempt retains its report in the attempt directory.

## Publication behavior

The command verifies the staged raw manifest/report, unique model IDs and manifest counts, strict metric JSON with exactly four approved definitions, and five evidence rows. It then replaces the three final `run_date` directories using sibling backups. If any replacement or finalization fails, prior directories are restored. `data/run_manifest.json` updates only after the complete publication succeeds. It records stage statuses, summaries, artifact paths and six SHA-256 hashes.

## Rerun and idempotency behavior

A same-date rerun uses a new attempt and overwrites complete final directories; it does not append API pages or metric rows. Business artifact bytes should match for unchanged inputs. Run IDs, timestamps and logs differ.

## Failure recovery

Inspect the failed `data/.runs/<run_id>/run_manifest.json` and `logs/pipeline.log`. Staged evidence remains in the attempt workspace when a stage fails. The latest successful manifest and previously published directories remain in place. Exit codes are 0 success, 1 configuration/extraction/runtime, 2 unhandled validation FAIL, 3 model, 4 metrics, and 5 publication/finalization.

## Artifact locations

Published: `data/raw/run_date=<RUN_DATE>/`, `data/processed/run_date=<RUN_DATE>/`, and `data/gold/run_date=<RUN_DATE>/`. Attempt diagnostics: `data/.runs/<run_id>/`. Latest successful summary: `data/run_manifest.json`. Source fixtures remain in `data/source/`.

## Known operational limitations

Local sibling renames provide rollback for a single process on one filesystem, not a cross-filesystem or multi-process transaction. No concurrent-writer lock, automated retention window, or operational cleanup policy is implemented. Source timezone and event-capture contracts remain unresolved. Phase 5 does not change business metric definitions or address assignment submission polish.
