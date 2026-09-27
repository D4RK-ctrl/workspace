"""Verify and safely publish a complete local pipeline attempt."""

import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
from uuid import uuid4


class PublicationError(RuntimeError):
    """A staged artifact or local publication contract failed."""


ARTIFACT_NAMES = {
    "raw_manifest": ("raw", "manifest.json"),
    "validation_report": ("raw", "validation_report.json"),
    "order_journey": ("processed", "order_journey.csv"),
    "model_manifest": ("processed", "model_manifest.json"),
    "metrics": ("gold", "metrics.json"),
    "evidence_table": ("gold", "evidence_table.csv"),
}
EXPECTED_METRIC_IDS = frozenset({
    "late_completed_delivery_rate", "median_lateness_minutes_among_late_orders",
    "median_creation_to_pickup_minutes", "late_rate_by_pre_delivery_intervention_exposure",
})


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid4().hex[:8]


def strict_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"),
                      parse_constant=lambda value: (_ for _ in ()).throw(
                          PublicationError(f"Non-finite JSON value in {path.name}: {value}")))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
                    encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_artifacts(directories: dict[str, Path], run_date: str) -> dict:
    """Check the three staged/published directories without changing business rules."""
    paths = {key: directories[stage] / name for key, (stage, name) in ARTIFACT_NAMES.items()}
    missing = [key for key, path in paths.items() if not path.is_file()]
    if missing:
        raise PublicationError(f"Required artifacts missing: {', '.join(missing)}")
    raw = strict_json(paths["raw_manifest"])
    report = strict_json(paths["validation_report"])
    model = strict_json(paths["model_manifest"])
    metrics = strict_json(paths["metrics"])
    if (raw.get("run_date") != run_date or model.get("run_date") != run_date
            or metrics.get("run_date") != run_date or "summary" not in report):
        raise PublicationError("Run-date or validation-report contract mismatch")
    with paths["order_journey"].open(encoding="utf-8", newline="") as stream:
        orders = list(csv.DictReader(stream))
    ids = [row.get("order_id") for row in orders]
    if (any(not key for key in ids) or len(ids) != len(set(ids))
            or model.get("output_order_rows") != len(orders)
            or model.get("output_unique_order_ids") != len(ids)):
        raise PublicationError("Published model order grain or manifest counts do not reconcile")
    metric_items = metrics.get("metrics")
    if (not isinstance(metric_items, list) or len(metric_items) != 4
            or {item.get("metric_id") for item in metric_items if isinstance(item, dict)} != EXPECTED_METRIC_IDS):
        raise PublicationError("Expected exactly the four approved primary metrics")
    with paths["evidence_table"].open(encoding="utf-8", newline="") as stream:
        evidence = list(csv.DictReader(stream))
    if len(evidence) != 5:
        raise PublicationError("Expected five evidence rows")
    return {"paths": paths, "raw": raw, "report": report, "model": model,
            "metrics": metrics, "order_count": len(orders), "evidence_count": len(evidence)}


def publish_attempt(staged: dict[str, Path], finals: dict[str, Path], latest: Path,
                    attempt_manifest: Path, manifest: dict, logger) -> dict:
    """Swap complete stage directories, restoring all old targets on failure."""
    run_id = manifest["run_id"]
    moved = []
    backups = []
    latest_temp = latest.with_name(f".{latest.name}.{run_id}.tmp")
    try:
        for stage in ("raw", "processed", "gold"):
            source, target = staged[stage], finals[stage]
            target.parent.mkdir(parents=True, exist_ok=True)
            backup = target.with_name(f".{target.name}.{run_id}.backup")
            if backup.exists():
                raise PublicationError(f"Backup destination already exists: {backup}")
            if target.exists():
                os.replace(target, backup)
                backups.append((target, backup))
            try:
                os.replace(source, target)
            except Exception:
                if backup.exists():
                    os.replace(backup, target)
                    backups.pop()
                raise
            moved.append((stage, source, target))
            logger.info("publish stage=%s target=%s", stage, target)

        checked = verify_artifacts(finals, manifest["run_date"])
        hashes = {key: sha256(path) for key, path in checked["paths"].items()}
        successful = {**manifest,
                      "completed_at": timestamp(), "overall_status": "SUCCESS", "exit_code": 0,
                      "artifact_locations": {key: str(path) for key, path in checked["paths"].items()},
                      "artifact_sha256": hashes}
        successful["stages"] = {**manifest["stages"], "publish": {
            "status": "SUCCESS", "started_at": manifest["stages"]["publish"]["started_at"],
            "completed_at": successful["completed_at"], "message": "All three directories published and verified"}}
        write_json(attempt_manifest, successful)
        write_json(latest_temp, successful)
        os.replace(latest_temp, latest)
    except Exception as exc:
        if latest_temp.exists():
            latest_temp.unlink()
        for stage, source, target in reversed(moved):
            if target.exists():
                os.replace(target, source)
            logger.error("publication rollback stage=%s", stage)
        for target, backup in reversed(backups):
            if backup.exists():
                os.replace(backup, target)
        raise PublicationError(f"Publication failed; previous output restored: {exc}") from exc
    for _, backup in backups:
        if backup.exists():
            try:
                shutil.rmtree(backup)
            except OSError as exc:
                logger.warning("Published successfully but backup cleanup failed: %s", exc)
    return successful
