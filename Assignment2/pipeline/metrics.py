"""Phase 4 descriptive metrics from the persisted order-grain model only."""

import csv
import json
from pathlib import Path
from statistics import median

from pipeline.clean import parse_timestamp


class MetricError(RuntimeError):
    """The model input or a metric consistency contract was violated."""


QUESTION = ("Where should FlashEats operations focus to reduce late deliveries, "
            "and is the available data trustworthy enough to identify the responsible workflow stage?")
CAUSAL_LIMIT = ("Interventions are not randomly assigned. Higher-risk or already-delayed "
                "orders may be more likely to receive intervention, so this comparison cannot "
                "establish causal effectiveness.")
PREP_LIMIT = ("Creation-to-pickup combines multiple operational stages because "
              "driver_arrived_at_restaurant is not observed. It is not restaurant preparation "
              "time, driver waiting time, or kitchen delay.")


def _boolean(value, field, order_id):
    if value is True or value == "True":
        return True
    if value is False or value == "False":
        return False
    raise MetricError(f"{field} must be a definite boolean for order {order_id}")


def _minutes(row, start, end):
    earlier, later = parse_timestamp(row.get(start)), parse_timestamp(row.get(end))
    if earlier is None or later is None:
        raise MetricError(f"Eligible order {row['order_id']} has an unparseable {start}/{end} timestamp")
    try:
        return (later - earlier).total_seconds() / 60
    except TypeError as exc:
        raise MetricError(f"Eligible order {row['order_id']} has incomparable {start}/{end} timestamps") from exc


def _percent(numerator, denominator):
    value = 100 * numerator / denominator if denominator else None
    if value is not None and not 0 <= value <= 100:
        raise MetricError("Metric percentage is outside 0..100")
    return value


def _metric(metric_id, label, value, unit, definition, exclusions, interpretation,
            limitations, **counts):
    return {"metric_id": metric_id, "label": label, "business_question": QUESTION,
            "value": value, "unit": unit, **counts, "definition": definition,
            "exclusions": exclusions, "interpretation": interpretation,
            "limitations": limitations}


def calculate_metrics(rows: list[dict], manifest: dict) -> dict:
    """Calculate exactly four primary metrics, failing on inconsistent eligible rows."""
    ids = [row.get("order_id") for row in rows]
    if any(not isinstance(key, str) or not key.strip() for key in ids) or len(ids) != len(set(ids)):
        raise MetricError("Input order_id must be non-empty and unique")
    total = len(rows)
    if manifest.get("output_order_rows") != total or manifest.get("output_unique_order_ids") != total:
        raise MetricError("Model manifest row counts do not match order_journey.csv")
    delay_rows, duration_rows = [], []
    for row in rows:
        if _boolean(row.get("delay_metric_eligible"), "delay_metric_eligible", row["order_id"]):
            delay_rows.append(row)
        if _boolean(row.get("duration_metric_eligible"), "duration_metric_eligible", row["order_id"]):
            duration_rows.append(row)
    if (manifest.get("delay_metric_eligible_orders") != len(delay_rows)
            or manifest.get("duration_metric_eligible_orders") != len(duration_rows)):
        raise MetricError("Model manifest eligibility counts do not reconcile")

    late_minutes = {}
    cohorts = {True: {"eligible_orders": 0, "late_orders": 0},
               False: {"eligible_orders": 0, "late_orders": 0}}
    for row in delay_rows:
        lateness = _minutes(row, "promised_eta", "actual_delivery_at")
        exposed = _boolean(row.get("has_pre_delivery_intervention"),
                           "has_pre_delivery_intervention", row["order_id"])
        cohorts[exposed]["eligible_orders"] += 1
        if lateness > 0:
            late_minutes[row["order_id"]] = lateness
            cohorts[exposed]["late_orders"] += 1
    durations = [_minutes(row, "created_at", "pickup_at") for row in duration_rows]
    if any(value < 0 for value in durations):
        raise MetricError("Eligible creation-to-pickup duration cannot be negative")
    late_count = len(late_minutes)
    if sum(group["eligible_orders"] for group in cohorts.values()) != len(delay_rows):
        raise MetricError("Intervention cohort denominators do not reconcile")
    if sum(group["late_orders"] for group in cohorts.values()) != late_count:
        raise MetricError("Intervention cohort late counts do not reconcile")
    for group in cohorts.values():
        group["late_rate_percent"] = _percent(group["late_orders"], group["eligible_orders"])

    delay_exclusions = {"total_model_rows": total, "not_delay_metric_eligible": total - len(delay_rows),
                        "eligible_delay_cohort": len(delay_rows), "late_eligible_orders": late_count}
    duration_exclusions = {"total_model_rows": total,
                           "not_duration_metric_eligible": total - len(duration_rows),
                           "eligible_duration_cohort": len(duration_rows)}
    late_rate = _metric(
        "late_completed_delivery_rate", "Late completed delivery rate",
        _percent(late_count, len(delay_rows)), "percent",
        "Eligible delivered orders with actual_delivery_at after the original promised_eta, divided by all delay_metric_eligible orders.",
        delay_exclusions, "Share of eligible completed deliveries that missed the original promise.",
        ["Conflicting order versions were excluded upstream; raw validation FAILs remain visible.",
         "The original promise is not replaced by dispatch's current ETA."],
        numerator=late_count, denominator=len(delay_rows))
    late_median = _metric(
        "median_lateness_minutes_among_late_orders", "Median lateness among late orders",
        median(late_minutes.values()) if late_minutes else None, "minutes",
        "Median actual_delivery_at minus original promised_eta among late delay_metric_eligible orders.",
        delay_exclusions, "Typical lateness severity among eligible late deliveries only.",
        ["On-time and delay-ineligible orders are outside this sample."], sample_size=late_count)
    pickup_median = _metric(
        "median_creation_to_pickup_minutes", "Median creation-to-pickup interval",
        median(durations) if durations else None, "minutes",
        "Median pickup_at minus created_at among duration_metric_eligible orders.",
        duration_exclusions, "Broad pre-pickup workflow interval, spanning several stages.",
        [PREP_LIMIT], sample_size=len(durations))
    intervention = _metric(
        "late_rate_by_pre_delivery_intervention_exposure", "Late rate by recorded pre-delivery intervention exposure",
        None, "percent",
        "Late completed delivery rate within each recorded pre-delivery intervention cohort of delay_metric_eligible orders.",
        delay_exclusions, "Descriptive comparison of eligible deliveries with and without a recorded pre-delivery intervention.",
        [CAUSAL_LIMIT, "Intervention capture completeness is unknown; false means no recorded pre-delivery intervention."],
        cohort_values={"exposed": cohorts[True], "unexposed": cohorts[False]})
    intervention.pop("value")
    metrics = [late_rate, late_median, pickup_median, intervention]
    if (late_rate["denominator"] != len(delay_rows) or late_median["sample_size"] != late_rate["numerator"]
            or pickup_median["sample_size"] != len(duration_rows)):
        raise MetricError("Primary metric denominators or sample sizes do not reconcile")
    return {"run_date": manifest["run_date"], "project_kpi": "late_completed_delivery_rate",
            "metrics": metrics,
            "limitations": ["Raw validation FAILs remain in the Phase 2 report.", PREP_LIMIT, CAUSAL_LIMIT]}


def read_model(model_dir: Path) -> tuple[list[dict], dict]:
    """Read only the two persisted Phase 3 model artifacts."""
    with (model_dir / "order_journey.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    manifest = json.loads((model_dir / "model_manifest.json").read_text(encoding="utf-8"),
                          parse_constant=lambda value: (_ for _ in ()).throw(MetricError(f"Non-finite model manifest value: {value}")))
    if not isinstance(manifest, dict) or manifest.get("run_date") != model_dir.name.removeprefix("run_date="):
        raise MetricError("Model manifest run_date does not match input directory")
    return rows, manifest


EVIDENCE_COLUMNS = ("metric_id", "metric_name", "value", "unit", "numerator", "denominator",
                    "sample_size", "business_question", "interpretation", "limitation")


def evidence_rows(metrics: dict) -> list[dict]:
    result = []
    for item in metrics["metrics"]:
        common = {"metric_name": item["label"], "unit": item["unit"],
                  "business_question": item["business_question"],
                  "interpretation": item["interpretation"],
                  "limitation": " ".join(item["limitations"])}
        if "cohort_values" in item:
            for cohort, name in (("exposed", "late_rate_intervention_exposed"),
                                 ("unexposed", "late_rate_no_intervention")):
                group = item["cohort_values"][cohort]
                result.append({**common, "metric_id": name, "value": group["late_rate_percent"],
                               "numerator": group["late_orders"], "denominator": group["eligible_orders"],
                               "sample_size": None})
        else:
            result.append({**common, "metric_id": item["metric_id"], "value": item["value"],
                           "numerator": item.get("numerator"), "denominator": item.get("denominator"),
                           "sample_size": item.get("sample_size")})
    return result


def write_metrics(result: dict, gold_root: Path) -> Path:
    """Write the two Phase 4 outputs; publication transactions belong to Phase 5."""
    destination = gold_root / f"run_date={result['run_date']}"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "metrics.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    with (destination / "evidence_table.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=EVIDENCE_COLUMNS)
        writer.writeheader()
        writer.writerows(evidence_rows(result))
    return destination
