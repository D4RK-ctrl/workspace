"""Attempt-scoped FlashEats pipeline with checked local publication."""

import argparse
from contextlib import contextmanager
from datetime import date
import json
import logging
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
from pipeline.clean import read_raw_artifacts
from pipeline.extract import ExtractionError, extract_csv, extract_dispatch, extract_orders
from pipeline.metrics import MetricError, calculate_metrics, read_model, write_metrics
from pipeline.logging_config import configure_logging
from pipeline.publish import (PublicationError, new_run_id, publish_attempt, timestamp,
                              verify_artifacts, write_json)
from pipeline.transform import HANDLED_MODEL_FAIL_IDS, ModelError, build_model, unhandled_validation_failures, write_model
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


def run(config: Config, raw_root: Path | None = None) -> Path:
    source = config.source_root
    raw_root = raw_root or config.raw_root
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
        logging.getLogger("flasheats").info("extract source=%s rows=%s pages=%s",
                                             result["source_name"], result["retrieved_record_count"],
                                             result.get("pages_retrieved"))
    print(f"[RAW] manifest written: {final / 'manifest.json'}")
    return final


def main() -> int:
    parser = argparse.ArgumentParser(description="FlashEats staged extract, validate, model, metrics, and publish")
    parser.add_argument("--run-date", required=True, help="logical run date (YYYY-MM-DD)")
    args = parser.parse_args()
    try:
        config = Config.from_environment(Path(__file__).resolve().parent, date.fromisoformat(args.run_date))
    except (ValueError, OSError) as exc:
        print(f"PIPELINE CONFIGURATION FAILED: {exc}", file=sys.stderr)
        return 1

    run_id = new_run_id()
    attempt = config.project_root / "data" / ".runs" / run_id
    try:
        attempt.mkdir(parents=True, exist_ok=False)
        logger = configure_logging(attempt, run_id, config.run_date.isoformat())
    except OSError as exc:
        print(f"PIPELINE RUNTIME FAILED: {exc}", file=sys.stderr)
        return 1
    manifest_path = attempt / "run_manifest.json"
    stages = {name: {"status": "PENDING", "started_at": None, "completed_at": None, "message": ""}
              for name in ("extract", "validate", "model", "metrics", "publish")}
    manifest = {"run_id": run_id, "run_date": config.run_date.isoformat(),
                "started_at": timestamp(), "completed_at": None, "overall_status": "RUNNING",
                "exit_code": None, "stages": stages, "artifact_locations": {},
                "validation_summary": None, "model_summary": None, "metric_ids": [],
                "handled_validation_fail_ids": [], "warnings_count": None,
                "unknown_count": None, "software": {"python_version": sys.version.split()[0]}}
    write_json(manifest_path, manifest)
    logger.info("pipeline start")
    print(f"[RUN] run_id={run_id} run_date={config.run_date.isoformat()}")

    def start(name):
        stages[name].update(status="RUNNING", started_at=timestamp(), message="Started")
        write_json(manifest_path, manifest)
        logger.info("stage=%s start", name)

    def done(name, message):
        stages[name].update(status="SUCCESS", completed_at=timestamp(), message=message)
        write_json(manifest_path, manifest)
        logger.info("stage=%s success %s", name, message)

    def fail(name, code, exc, blocked=False):
        stages[name].update(status="BLOCKED" if blocked else "FAILED",
                            completed_at=timestamp(), message=str(exc))
        for stage in stages.values():
            if stage["status"] == "PENDING":
                stage["status"] = "BLOCKED"
                stage["message"] = f"Earlier stage {name} did not complete"
        manifest.update(overall_status="FAILED", exit_code=code, completed_at=timestamp())
        write_json(manifest_path, manifest)
        logger.error("stage=%s failed exit_code=%s error=%s", name, code, exc)
        print(f"PIPELINE {name.upper()} FAILED: {exc}", file=sys.stderr)
        return code

    start("extract")
    try:
        raw_dir = run(config, attempt / "raw")
        done("extract", "Four sources retrieved into attempt workspace")
    except (ValueError, OSError, ExtractionError) as exc:
        return fail("extract", 1, exc)

    start("validate")
    try:
        report = validate_run(raw_dir)
        summary = report["summary"]
        unhandled = unhandled_validation_failures(report)
        handled = sorted(check["check_id"] for check in report["checks"]
                         if check["status"] == "FAIL" and check["check_id"] in HANDLED_MODEL_FAIL_IDS)
        print(f"[VALIDATE] {report['overall_status']} "
              f"(pass={summary['pass']} warn={summary['warn']} "
              f"fail={summary['fail']} unknown={summary['unknown']})")
        print(f"[VALIDATE] report written: {raw_dir / 'validation_report.json'}")
        manifest["validation_summary"] = summary
        manifest["warnings_count"] = summary["warn"]
        manifest["unknown_count"] = summary["unknown"]
        manifest["handled_validation_fail_ids"] = handled
        logger.info("validation status=%s summary=%s handled=%s unhandled=%s",
                    report["overall_status"], summary, handled, unhandled)
        if unhandled:
            print(f"[VALIDATE] unhandled FAIL blocks modelling: {', '.join(unhandled)}")
            return fail("validate", 2, f"Unhandled validation FAIL: {', '.join(unhandled)}", blocked=True)
        if handled:
            print(f"[VALIDATE] handled modelling exceptions: {', '.join(handled)}")
        done("validate", "Validation report saved; no unhandled FAIL")
    except (ValueError, OSError, ExtractionError) as exc:
        return fail("validate", 1, exc)

    start("model")
    try:
        raw = read_raw_artifacts(raw_dir)
        journey, model_manifest = build_model(raw, config.run_date.isoformat(), report)
        output = write_model(journey, model_manifest, attempt / "processed")
        manifest["model_summary"] = {"output_order_rows": model_manifest["output_order_rows"],
                                     "excluded_conflicting_orders": model_manifest["conflicting_order_ids"],
                                     "delay_metric_eligible_orders": model_manifest["delay_metric_eligible_orders"],
                                     "duration_metric_eligible_orders": model_manifest["duration_metric_eligible_orders"]}
        logger.info("model rows=%s excluded_conflicts=%s",
                    model_manifest["output_order_rows"], model_manifest["conflicting_order_ids"])
        done("model", f"{model_manifest['output_order_rows']} unique canonical orders")
    except (ModelError, OSError, ValueError, TypeError, KeyError) as exc:
        return fail("model", 3, exc)
    print(f"[MODEL] canonical orders: {model_manifest['output_order_rows']}")
    print(f"[MODEL] excluded conflicts: {model_manifest['conflicting_order_ids']}")
    print(f"[MODEL] order_journey written: {output / 'order_journey.csv'}")
    print(f"[MODEL] manifest written: {output / 'model_manifest.json'}")
    start("metrics")
    try:
        model_rows, persisted_manifest = read_model(output)
        metric_result = calculate_metrics(model_rows, persisted_manifest)
        gold_dir = write_metrics(metric_result, attempt / "gold")
        manifest["metric_ids"] = [item["metric_id"] for item in metric_result["metrics"]]
        logger.info("metrics completed ids=%s", manifest["metric_ids"])
        done("metrics", "Four primary metrics and five evidence rows written")
    except (MetricError, OSError, ValueError, TypeError, KeyError, OverflowError) as exc:
        return fail("metrics", 4, exc)
    for item in metric_result["metrics"][:3]:
        print(f"[METRICS] {item['metric_id']}: {item['value']}")
    print("[METRICS] intervention cohorts written")
    print(f"[METRICS] metrics.json written: {gold_dir / 'metrics.json'}")

    start("publish")
    staged = {"raw": raw_dir, "processed": output, "gold": gold_dir}
    finals = {name: config.project_root / "data" / name / f"run_date={config.run_date.isoformat()}"
              for name in staged}
    try:
        verify_artifacts(staged, config.run_date.isoformat())
        latest = config.project_root / "data" / "run_manifest.json"
        publish_attempt(staged, finals, latest, manifest_path, manifest, logger)
    except (PublicationError, OSError, ValueError, TypeError, KeyError) as exc:
        return fail("publish", 5, exc)
    logger.info("stage=publish success latest_manifest=%s", latest)
    print(f"[PUBLISH] latest successful manifest: {latest}")
    print("PHASE 5 COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
