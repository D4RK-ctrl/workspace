"""Conservative Phase 3 preparation of validated raw source values."""

from collections import defaultdict
import csv
from datetime import datetime
import json
from pathlib import Path


def parse_timestamp(value):
    """Return a parsed value for modelling; raw text remains in every output row."""
    if value is None or not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def comparable(left, right):
    return left is not None and right is not None and (left.tzinfo is None) == (right.tzinfo is None)


def read_raw_artifacts(raw_dir: Path) -> dict:
    """Read only Phase 1 preserved artifacts; validation precedes this call."""
    with (raw_dir / "sql" / "orders.jsonl").open(encoding="utf-8") as stream:
        orders = [json.loads(line) for line in stream]
    files = {}
    for name in ("customer_app_actions", "order_interventions"):
        with (raw_dir / "files" / f"{name}.csv").open(encoding="utf-8-sig", newline="") as stream:
            files[name] = list(csv.DictReader(stream))
    dispatch = []
    for path in sorted((raw_dir / "api").glob("page_*.json")):
        dispatch.extend(json.loads(path.read_bytes())["data"])
    return {"orders": orders, "customer_app_actions": files["customer_app_actions"],
            "order_interventions": files["order_interventions"], "dispatch": dispatch}


def _fingerprint(row):
    return json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False)


def _normalized(value):
    return value.strip().lower() if isinstance(value, str) else value


def prepare_orders(raw_orders: list[dict]) -> tuple[list[dict], dict]:
    """Collapse only exact duplicates; exclude all conflicting versions with provenance."""
    groups = defaultdict(list)
    for row in raw_orders:
        groups[row["order_id"]].append(row)
    canonical = []
    exact_ids = []
    excluded = []
    for order_id, versions in groups.items():
        if len({_fingerprint(row) for row in versions}) > 1:
            excluded.append({"order_id": order_id, "source_row_count": len(versions),
                             "model_excluded": True,
                             "model_exclusion_reason": "conflicting_order_versions"})
            continue
        if len(versions) > 1:
            exact_ids.append(order_id)
        raw = versions[0]
        times = {field: parse_timestamp(raw.get(field)) for field in
                 ("created_at", "promised_eta", "pickup_at", "actual_delivery_at")}
        malformed = any(raw.get(field) not in (None, "") and times[field] is None for field in times)
        chronology_valid = not malformed
        for later, earlier in (("promised_eta", "created_at"),
                               ("pickup_at", "created_at"),
                               ("actual_delivery_at", "pickup_at")):
            left, right = times[later], times[earlier]
            if left is not None and right is not None:
                if not comparable(left, right) or left < right:
                    chronology_valid = False
        duration_interval_valid = (comparable(times["pickup_at"], times["created_at"])
                                   and times["created_at"] <= times["pickup_at"])
        status_norm = _normalized(raw.get("final_status"))
        row = {
            "order_id": order_id, "customer_id": raw.get("customer_id"),
            "restaurant_id": raw.get("restaurant_id"), "sql_driver_id": raw.get("driver_id"),
            "created_at": raw.get("created_at"), "promised_eta": raw.get("promised_eta"),
            "pickup_at": raw.get("pickup_at"), "actual_delivery_at": raw.get("actual_delivery_at"),
            "final_status_raw": raw.get("final_status"), "final_status_norm": status_norm,
            "traffic_bucket_raw": raw.get("traffic_bucket"),
            "traffic_bucket_norm": _normalized(raw.get("traffic_bucket")),
            "weather_bucket_raw": raw.get("weather_bucket"),
            "weather_bucket_norm": _normalized(raw.get("weather_bucket")),
            "city": raw.get("city"), "distance_km_estimate": raw.get("distance_km_estimate"),
            "source_order_row_count": len(versions), "exact_duplicate_collapsed": len(versions) > 1,
            "model_excluded": False, "model_exclusion_reason": None,
            "chronology_valid": chronology_valid,
            "delay_metric_eligible": (status_norm == "delivered" and times["promised_eta"] is not None
                                      and times["actual_delivery_at"] is not None and chronology_valid),
            "duration_metric_eligible": bool(duration_interval_valid),
        }
        canonical.append(row)
    stats = {
        "input_order_rows": len(raw_orders), "input_unique_order_ids": len(groups),
        "exact_duplicate_order_ids": len(exact_ids), "exact_duplicate_ids": sorted(exact_ids),
        "conflicting_order_ids": len(excluded),
        "excluded_conflicting_order_ids": sorted(excluded, key=lambda item: item["order_id"]),
    }
    return canonical, stats
