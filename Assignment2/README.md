# FDE Assignment 2 — Track A: FlashEats

This repository currently implements **Phase 1 extraction only**. It retrieves complete orders from SQLite, two CSV sources, and paginated dispatch records through the bundled mock REST API. It preserves raw evidence and writes a machine-readable manifest. Cleaning, lifecycle validation, modelling, and metrics are reserved for later phases.

Use Python 3.10 or newer. From `Assignment2/`:

```sh
python -m pip install -r requirements.txt
python run_pipeline.py --run-date 2026-08-28
```

The command starts the bundled mock API if the configured local endpoint is not already healthy. No notebook or separate API command is needed. Output appears under `data/raw/run_date=YYYY-MM-DD/`; a successful same-date rerun replaces that directory instead of appending files. The included files under `data/source/` allow a clean clone to run without the instructor repositories.

Configuration uses environment variables documented in `.env.example`; the example file is not automatically loaded. `DISPATCH_API_URL` may point to an already running compatible API. Automatic startup of the bundled mock applies to the default local endpoint. A failed extraction exits nonzero and leaves the last successful run-date directory intact.

Run the focused tests with `python -m unittest discover -s tests -v`.
