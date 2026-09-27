# FDE Assignment 2 — Track A: FlashEats

This repository currently implements **Extract -> Validate -> Model -> Metrics -> Publish** through Phase 5. It retrieves complete orders from SQLite, two CSV sources, and paginated dispatch records through the bundled mock REST API. It preserves raw evidence, profiles the four sources, builds a transparent one-row-per-order workflow model, and calculates four descriptive business metrics.

Use Python 3.10 or newer. From `Assignment2/`:

```sh
python -m pip install -r requirements.txt
python run_pipeline.py --run-date YYYY-MM-DD
```

The command starts the bundled mock API if the configured local endpoint is not already healthy. No notebook or separate API command is needed. Raw evidence, `manifest.json`, and `validation_report.json` appear under `data/raw/run_date=YYYY-MM-DD/`. The model appears under `data/processed/run_date=YYYY-MM-DD/order_journey.csv` with `model_manifest.json` beside it. Metrics appear under `data/gold/run_date=YYYY-MM-DD/metrics.json` and `data/gold/run_date=YYYY-MM-DD/evidence_table.csv`. Each run builds in `data/.runs/<run_id>/` and publishes complete, checked stage directories together. A failed attempt retains diagnostics there and does not replace the latest successful `data/run_manifest.json`. Its log is `data/.runs/<run_id>/logs/pipeline.log`. The included files under `data/source/` allow a clean clone to run without the instructor repositories.

Configuration uses environment variables documented in `.env.example`; the example file is not automatically loaded. `DISPATCH_API_URL` may point to an already running compatible API. Automatic startup of the bundled mock applies to the default local endpoint. Exit code `0` means all approved stages completed, `1` means configuration/extraction/validation runtime failure, `2` means an unhandled validation FAIL blocked modelling, `3` means model construction failed, `4` means metric calculation or consistency failed, and `5` means publication/finalization failed. The four approved raw quality FAIL checks remain FAIL in `validation_report.json`; the model excludes conflicting orders and flags chronology issues rather than silently repairing them. See `docs/validation_contract.md`, `docs/workflow_model.md`, `docs/metric_definitions.md`, and `docs/pipeline_operations.md` for the rules and operations.

Run the focused tests with `python -m unittest discover -s tests -v`.
