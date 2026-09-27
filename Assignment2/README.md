# FDE Assignment 2 — Track A: FlashEats

This repository currently implements **Extract -> Validate** through Phase 2. It retrieves complete orders from SQLite, two CSV sources, and paginated dispatch records through the bundled mock REST API. It preserves raw evidence, profiles the four sources, and writes a machine-readable validation report. Cleaning, modelling, and metrics are reserved for later phases.

Use Python 3.10 or newer. From `Assignment2/`:

```sh
python -m pip install -r requirements.txt
python run_pipeline.py --run-date 2026-08-28
```

The command starts the bundled mock API if the configured local endpoint is not already healthy. No notebook or separate API command is needed. Raw evidence, `manifest.json`, and `validation_report.json` appear under `data/raw/run_date=YYYY-MM-DD/`. A same-date rerun replaces that directory instead of appending files. The included files under `data/source/` allow a clean clone to run without the instructor repositories.

Configuration uses environment variables documented in `.env.example`; the example file is not automatically loaded. `DISPATCH_API_URL` may point to an already running compatible API. Automatic startup of the bundled mock applies to the default local endpoint. Exit code `0` means extraction succeeded and validation is PASS or WARN, `1` means configuration/extraction/runtime failure, and `2` means validation produced FAIL after writing its report. FAIL blocks later modelling or KPI publication. See `docs/validation_contract.md` for the rules and status meanings.

Run the focused tests with `python -m unittest discover -s tests -v`.
