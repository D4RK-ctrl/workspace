"""Phase 3 order-grain workflow model; no KPI calculations."""

from collections import defaultdict
import csv
import json
from pathlib import Path
import shutil
import tempfile

from pipeline.clean import comparable, parse_timestamp, prepare_orders


class ModelError(RuntimeError):
    """A parent-grain or child-cardinality contract was violated."""


HANDLED_MODEL_FAIL_IDS = frozenset({
    "orders_conflicting_duplicate_ids",
    "orders_parent_grain",
    "orders_promise_chronology",
    "orders_milestone_chronology",
})


def unhandled_validation_failures(report: dict) -> list[str]:
    """Only the four approved, explicitly modelled raw FAILs may proceed."""
    failures = [check["check_id"] for check in report["checks"] if check["status"] == "FAIL"]
    unhandled = {check_id for check_id in failures if check_id not in HANDLED_MODEL_FAIL_IDS}
    if report["overall_status"] == "FAIL" and not failures:
        unhandled.add("unexplained_validation_fail")
    return sorted(unhandled)


APP_COUNT_FIELDS = ("app_action_count_total", "eta_viewed_count", "support_opened_count",
                    "cancel_attempted_count", "pre_delivery_action_count",
                    "post_delivery_action_count", "unclassified_action_count")
INTERVENTION_COUNT_FIELDS = ("intervention_count_total", "pre_delivery_intervention_count",
                             "post_delivery_intervention_count", "unclassified_intervention_count",
                             "driver_reassignment_count", "restaurant_contact_count",
                             "priority_dispatch_count", "customer_credit_count")
DISPATCH_FIELDS = ("dispatch_driver_id", "dispatch_original_driver_id", "dispatch_assigned_at",
                   "dispatch_reassigned_at", "dispatch_estimated_pickup_at",
                   "dispatch_current_delivery_eta", "dispatch_status", "eta_model_version",
                   "driver_assignment_changed")

OUTPUT_COLUMNS = (
    "order_id", "customer_id", "restaurant_id", "sql_driver_id", "created_at", "promised_eta",
    "pickup_at", "actual_delivery_at", "final_status_raw", "final_status_norm",
    "traffic_bucket_raw", "traffic_bucket_norm", "weather_bucket_raw", "weather_bucket_norm",
    "city", "distance_km_estimate", "source_order_row_count", "exact_duplicate_collapsed",
    "model_excluded", "model_exclusion_reason", "chronology_valid", "delay_metric_eligible",
    "duration_metric_eligible", *APP_COUNT_FIELDS, "first_action_at", "last_action_at",
    *INTERVENTION_COUNT_FIELDS, "first_intervention_at", "last_intervention_at",
    "has_pre_delivery_intervention", *DISPATCH_FIELDS,
)


def _usable(value):
    return isinstance(value, str) and bool(value.strip())


def _first_last(rows, field):
    parsed = [(parse_timestamp(row.get(field)), row.get(field)) for row in rows]
    parsed = [(stamp, raw) for stamp, raw in parsed if stamp is not None]
    if not parsed or len({stamp.tzinfo is None for stamp, _ in parsed}) > 1:
        return None, None
    return min(parsed, key=lambda item: item[0])[1], max(parsed, key=lambda item: item[0])[1]


def _event_position(value, parent):
    """Classify only directly comparable observed times; otherwise leave unclassified."""
    event = parse_timestamp(value)
    if parent is None or event is None:
        return "unclassified"
    created = parse_timestamp(parent.get("created_at"))
    delivered = parse_timestamp(parent.get("actual_delivery_at"))
    if comparable(event, delivered) and event > delivered:
        return "post"
    if (comparable(event, created) and comparable(event, delivered)
            and created <= event <= delivered):
        return "pre"
    return "unclassified"


def _group_children(rows):
    grouped = defaultdict(list)
    missing = 0
    for row in rows:
        if _usable(row.get("order_id")):
            grouped[row["order_id"]].append(row)
        else:
            missing += 1
    return grouped, missing


def aggregate_app_actions(rows: list[dict], parents: dict) -> tuple[list[dict], dict]:
    grouped, missing = _group_children(rows)
    aggregate = []
    for order_id, actions in grouped.items():
        counts = {field: 0 for field in APP_COUNT_FIELDS}
        counts["app_action_count_total"] = len(actions)
        for action in actions:
            field = {"ETA_VIEWED": "eta_viewed_count", "SUPPORT_OPENED": "support_opened_count",
                     "CANCEL_ATTEMPTED": "cancel_attempted_count"}.get(action.get("action_type"))
            if field:
                counts[field] += 1
            timing = _event_position(action.get("action_at"), parents.get(order_id))
            counts[{"pre": "pre_delivery_action_count", "post": "post_delivery_action_count",
                    "unclassified": "unclassified_action_count"}[timing]] += 1
        first, last = _first_last(actions, "action_at")
        aggregate.append({"order_id": order_id, **counts, "first_action_at": first, "last_action_at": last})
    summary = {"input_rows": len(rows), "orders_with_actions": len(grouped),
               "rows_without_usable_order_id": missing,
               "rows_not_joined_to_canonical_parent": sum(len(group) for key, group in grouped.items()
                                                          if key not in parents)}
    return aggregate, summary


def aggregate_interventions(rows: list[dict], parents: dict) -> tuple[list[dict], dict]:
    grouped, missing = _group_children(rows)
    aggregate = []
    for order_id, interventions in grouped.items():
        counts = {field: 0 for field in INTERVENTION_COUNT_FIELDS}
        counts["intervention_count_total"] = len(interventions)
        for intervention in interventions:
            field = {"DRIVER_REASSIGNMENT": "driver_reassignment_count",
                     "RESTAURANT_CONTACT": "restaurant_contact_count",
                     "PRIORITY_DISPATCH": "priority_dispatch_count",
                     "CUSTOMER_CREDIT": "customer_credit_count"}.get(intervention.get("intervention_type"))
            if field:
                counts[field] += 1
            timing = _event_position(intervention.get("intervention_at"), parents.get(order_id))
            counts[{"pre": "pre_delivery_intervention_count", "post": "post_delivery_intervention_count",
                    "unclassified": "unclassified_intervention_count"}[timing]] += 1
        first, last = _first_last(interventions, "intervention_at")
        aggregate.append({"order_id": order_id, **counts,
                          "first_intervention_at": first, "last_intervention_at": last,
                          "has_pre_delivery_intervention": counts["pre_delivery_intervention_count"] > 0})
    summary = {"input_rows": len(rows), "orders_with_interventions": len(grouped),
               "rows_without_usable_order_id": missing,
               "rows_not_joined_to_canonical_parent": sum(len(group) for key, group in grouped.items()
                                                          if key not in parents)}
    return aggregate, summary


def prepare_dispatch(rows: list[dict]) -> list[dict]:
    seen = set()
    prepared = []
    for row in rows:
        order_id = row.get("order_id")
        if not _usable(order_id) or order_id in seen:
            raise ModelError("Dispatch requires a unique, non-empty order_id before joining")
        seen.add(order_id)
        current, original = row.get("driver_id"), row.get("original_driver_id")
        prepared.append({
            "order_id": order_id, "dispatch_driver_id": current,
            "dispatch_original_driver_id": original,
            "dispatch_assigned_at": row.get("assigned_at"),
            "dispatch_reassigned_at": row.get("reassigned_at"),
            "dispatch_estimated_pickup_at": row.get("estimated_pickup_at"),
            "dispatch_current_delivery_eta": row.get("current_delivery_eta"),
            "dispatch_status": row.get("dispatch_status"),
            "eta_model_version": row.get("eta_model_version"),
            "driver_assignment_changed": current != original if _usable(current) and _usable(original) else None,
        })
    return prepared


def _left_join(parents: list[dict], children: list[dict], name: str, defaults: dict) -> tuple[list[dict], dict]:
    parent_ids = [row["order_id"] for row in parents]
    if len(parent_ids) != len(set(parent_ids)):
        raise ModelError("Canonical parent order_id is not unique")
    child_ids = [row["order_id"] for row in children]
    if len(child_ids) != len(set(child_ids)):
        raise ModelError(f"{name} has more than one aggregate row per order_id")
    by_id = {row["order_id"]: row for row in children}
    joined = [{**parent, **{key: value for key, value in by_id.get(parent["order_id"], defaults).items()
                          if key != "order_id"}} for parent in parents]
    output_ids = [row["order_id"] for row in joined]
    if len(joined) != len(parents) or len(set(output_ids)) != len(set(parent_ids)) or set(output_ids) != set(parent_ids):
        raise ModelError(f"{name} join changed the canonical order grain")
    check = {"join": name, "parent_rows_before": len(parents), "rows_after": len(joined),
             "unique_order_ids_before": len(set(parent_ids)),
             "unique_order_ids_after": len(set(output_ids)),
             "child_rows": len(children), "child_unique_order_ids": len(set(child_ids)),
             "parent_grain_preserved": True}
    return joined, check


def build_model(raw: dict, run_date: str, validation_report: dict) -> tuple[list[dict], dict]:
    unhandled = unhandled_validation_failures(validation_report)
    if unhandled:
        raise ModelError(f"Unhandled validation FAIL blocks modelling: {', '.join(unhandled)}")
    canonical, order_stats = prepare_orders(raw["orders"])
    parents = {row["order_id"]: row for row in canonical}
    if len(parents) != len(canonical):
        raise ModelError("Canonical order preparation did not produce unique order IDs")
    actions, action_summary = aggregate_app_actions(raw["customer_app_actions"], parents)
    interventions, intervention_summary = aggregate_interventions(raw["order_interventions"], parents)
    dispatch = prepare_dispatch(raw["dispatch"])
    defaults_actions = {**{field: 0 for field in APP_COUNT_FIELDS},
                        "first_action_at": None, "last_action_at": None}
    defaults_interventions = {**{field: 0 for field in INTERVENTION_COUNT_FIELDS},
                              "first_intervention_at": None, "last_intervention_at": None,
                              "has_pre_delivery_intervention": False}
    defaults_dispatch = {field: None for field in DISPATCH_FIELDS}
    journey, action_check = _left_join(canonical, actions, "customer_app_actions", defaults_actions)
    journey, intervention_check = _left_join(journey, interventions, "order_interventions", defaults_interventions)
    journey, dispatch_check = _left_join(journey, dispatch, "dispatch", defaults_dispatch)
    if any(set(row) != set(OUTPUT_COLUMNS) for row in journey):
        raise ModelError("Journey columns do not match the documented order-grain model")
    handled_fails = sorted(check["check_id"] for check in validation_report["checks"] if check["status"] == "FAIL")
    manifest = {
        "run_date": run_date, **order_stats,
        "output_order_rows": len(journey), "output_unique_order_ids": len({row["order_id"] for row in journey}),
        "chronology_invalid_orders": sum(not row["chronology_valid"] for row in journey),
        "delay_metric_eligible_orders": sum(row["delay_metric_eligible"] for row in journey),
        "duration_metric_eligible_orders": sum(row["duration_metric_eligible"] for row in journey),
        "child_aggregation_summaries": {
            "customer_app_actions": action_summary, "order_interventions": intervention_summary,
            "dispatch": {"input_rows": len(raw["dispatch"]), "unique_order_ids": len(dispatch)},
        },
        "join_row_count_checks": [action_check, intervention_check, dispatch_check],
        "validation_overall_status": validation_report["overall_status"],
        "handled_validation_fail_check_ids": handled_fails,
        "known_limitations": [
            "App and intervention capture completeness is unknown; zero joined counts mean no recorded child rows.",
            "Driver arrival at the restaurant is unobserved; restaurant and driver delay stages cannot be separated.",
            "Source timezone has no approved contract; no timezone was assigned.",
            "Intervention presence is descriptive and does not establish causal effectiveness.",
        ],
    }
    return journey, manifest


def write_model(journey: list[dict], manifest: dict, processed_root: Path) -> Path:
    """Replace the deterministic generated run directory after model construction succeeds."""
    processed_root.mkdir(parents=True, exist_ok=True)
    final = processed_root / f"run_date={manifest['run_date']}"
    with tempfile.TemporaryDirectory(prefix=".phase3-", dir=processed_root) as temporary:
        stage = Path(temporary)
        with (stage / "order_journey.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=OUTPUT_COLUMNS)
            writer.writeheader()
            writer.writerows(journey)
        (stage / "model_manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
        if final.exists():
            if final.parent.resolve() != processed_root.resolve() or not final.name.startswith("run_date="):
                raise ModelError(f"Unsafe processed-output destination: {final}")
            shutil.rmtree(final)
        shutil.move(str(stage), str(final))
    return final
