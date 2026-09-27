"""Command-line entry point for Phase 2 extract and validate."""

import argparse
from contextlib import contextmanager
from datetime import date
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import urlopen

from pipeline.config import Config
from pipeline.extract import ExtractionError, extract_csv, extract_dispatch, extract_orders
from pipeline.validate import validate_run


def _api_ready(api_url: str) -> bool:
    try:
        with urlopen(api_url.rstrip("/") + "/health", timeout=1) as response:
            payload = json.loads(response.read())
            return response.status == 200 and payload.get("service") == "flasheats-dispatch-api"
    except (HTTPError, URLError, TimeoutError, ValueError, AttributeError):
        return False


@contextmanager
def available_api(config: Config):
    """Use a healthy API, or own and clean up a copied local mock process."""
    process = None
    try:
        if not _api_ready(config.api_url):
            parsed = urlparse(config.api_url)
            if parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.port != 8000 or parsed.path not in {"", "/"}:
                raise ExtractionError("Configured dispatch API is unavailable; bundled mock starts only at local port 8000")
            script = config.source_root / "api" / "mock_dispatch_api.py"
            if not script.is_file():
                raise ExtractionError(f"Bundled mock API missing: {script}")
            process = subprocess.Popen(
                [sys.executable, "-B", str(script)],
                cwd=script.parent,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            for _ in range(30):
                if _api_ready(config.api_url):
                    break
                if process.poll() is not None:
                    raise ExtractionError("Bundled mock API exited before becoming ready; check Flask installation")
                time.sleep(0.2)
            else:
                raise ExtractionError("Bundled mock API did not become ready within 6 seconds")
        yield
    finally:
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)


def run(config: Config) -> Path:
    source = config.source_root
    raw_root = config.raw_root
    raw_root.mkdir(parents=True, exist_ok=True)
    final = raw_root / f"run_date={config.run_date.isoformat()}"
    with tempfile.TemporaryDirectory(prefix=".phase1-", dir=raw_root) as temporary:
        stage = Path(temporary)
        with available_api(config):
            results = [
                extract_orders(source / "database" / "flasheats.db", stage / "sql" / "orders.jsonl"),
                extract_csv(source / "files" / "customer_app_actions.csv", stage / "files" / "customer_app_actions.csv", "customer_app_actions"),
                extract_csv(source / "files" / "order_interventions.csv", stage / "files" / "order_interventions.csv", "order_interventions"),
                extract_dispatch(config.api_url, config.api_timeout_seconds, config.api_max_retries,
                                 config.api_page_size, stage / "api"),
            ]
        manifest = {"run_date": config.run_date.isoformat(), "status": "complete", "sources": results}
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        if final.exists():
            # The only removable path is this deterministic generated run directory.
            if final.parent.resolve() != raw_root.resolve() or not final.name.startswith("run_date="):
                raise ExtractionError(f"Unsafe raw-output destination: {final}")
            shutil.rmtree(final)
        shutil.move(str(stage), str(final))
    for result in results:
        pages = f", {result['pages_retrieved']} pages" if "pages_retrieved" in result else ""
        print(f"[EXTRACT] {result['source_name']}: OK ({result['retrieved_record_count']} records{pages})")
    print(f"[RAW] manifest written: {final / 'manifest.json'}")
    return final


def main() -> int:
    parser = argparse.ArgumentParser(description="FlashEats Phase 1 raw source extraction")
    parser.add_argument("--run-date", required=True, help="logical run date (YYYY-MM-DD)")
    args = parser.parse_args()
    try:
        config = Config.from_environment(Path(__file__).resolve().parent, date.fromisoformat(args.run_date))
        raw_dir = run(config)
        report = validate_run(raw_dir)
        summary = report["summary"]
        print(f"[VALIDATE] {report['overall_status']} "
              f"(pass={summary['pass']} warn={summary['warn']} "
              f"fail={summary['fail']} unknown={summary['unknown']})")
        print(f"[VALIDATE] report written: {raw_dir / 'validation_report.json'}")
        if report["overall_status"] == "FAIL":
            print("PHASE 2 VALIDATION FAILED")
            return 2
        print("PHASE 2 COMPLETE")
        return 0
    except (ValueError, OSError, ExtractionError) as exc:
        print(f"PHASE 2 PIPELINE FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
