# FDE Assignment 2 — Track A: FlashEats

This repository currently implements **Extract -> Validate -> Model -> Metrics** through Phase 4. It retrieves complete orders from SQLite, two CSV sources, and paginated dispatch records through the bundled mock REST API. It preserves raw evidence, profiles the four sources, builds a transparent one-row-per-order workflow model, and calculates four descriptive business metrics.

Use Python 3.10 or newer. From `Assignment2/`:

```sh
python -m pip install -r requirements.txt
python run_pipeline.py --run-date 2026-08-28
```

The command starts the bundled mock API if the configured local endpoint is not already healthy. No notebook or separate API command is needed. Raw evidence, `manifest.json`, and `validation_report.json` appear under `data/raw/run_date=YYYY-MM-DD/`. The model appears under `data/processed/run_date=YYYY-MM-DD/order_journey.csv` with `model_manifest.json` beside it. Metrics appear under `data/gold/run_date=YYYY-MM-DD/metrics.json` and `data/gold/run_date=YYYY-MM-DD/evidence_table.csv`. A same-date rerun replaces the generated raw and processed directories and overwrites the two gold files. The included files under `data/source/` allow a clean clone to run without the instructor repositories.

Configuration uses environment variables documented in `.env.example`; the example file is not automatically loaded. `DISPATCH_API_URL` may point to an already running compatible API. Automatic startup of the bundled mock applies to the default local endpoint. Exit code `0` means all approved stages completed, `1` means configuration/extraction/validation runtime failure, `2` means an unhandled validation FAIL blocked modelling, `3` means model construction failed, and `4` means metric calculation or consistency failed. The four approved raw quality FAIL checks remain FAIL in `validation_report.json`; the model excludes conflicting orders and flags chronology issues rather than silently repairing them. See `docs/validation_contract.md`, `docs/workflow_model.md`, and `docs/metric_definitions.md` for the rules and definitions.

Run the focused tests with `python -m unittest discover -s tests -v`.
