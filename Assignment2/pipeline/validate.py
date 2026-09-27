"""Phase 2 validation of preserved Phase 1 artifacts; no source values are changed."""

from collections import Counter, defaultdict
import csv
from datetime import date, datetime
import hashlib
import json
import math
from pathlib import Path

REQUIRED = {
    "orders": ("order_id", "customer_id", "restaurant_id", "driver_id", "created_at",
               "promised_eta", "pickup_at", "actual_delivery_at", "final_status", "city",
               "distance_km_estimate", "traffic_bucket", "weather_bucket"),
    "customer_app_actions": ("action_id", "order_id", "customer_id", "action_type", "action_at", "channel"),
    "order_interventions": ("intervention_id", "order_id", "intervention_type", "intervention_at", "initiated_by", "reason"),
    "dispatch": ("order_id", "driver_id", "original_driver_id", "assigned_at", "reassigned_at",
                 "estimated_pickup_at", "current_delivery_eta", "dispatch_status", "eta_model_version"),
}
KEY = {"orders": "order_id", "customer_app_actions": "action_id",
       "order_interventions": "intervention_id", "dispatch": "order_id"}
TIME_FIELDS = {
    "orders": ("created_at", "promised_eta", "pickup_at", "actual_delivery_at"),
    "customer_app_actions": ("action_at",),
    "order_interventions": ("intervention_at",),
    "dispatch": ("assigned_at", "reassigned_at", "estimated_pickup_at", "current_delivery_eta"),
}
# Provisional observed vocabularies only; values are never normalized or replaced.
CATEGORIES = {
    "orders": {"final_status": {"delivered", "cancelled"},
               "traffic_bucket": {"low", "medium", "high", "severe"},
               "weather_bucket": {"clear", "rain", "heavy_rain"}},
    "customer_app_actions": {"action_type": {"ETA_VIEWED", "SUPPORT_OPENED", "CANCEL_ATTEMPTED"}},
    "order_interventions": {"intervention_type": {"DRIVER_REASSIGNMENT", "RESTAURANT_CONTACT",
                                                  "PRIORITY_DISPATCH", "CUSTOMER_CREDIT"}},
    "dispatch": {"dispatch_status": {"completed", "cancelled"}},
}
PATHS = {"orders": "sql/orders.jsonl",
         "customer_app_actions": "files/customer_app_actions.csv",
         "order_interventions": "files/order_interventions.csv"}


def _json(text):
    def reject(value):
        raise ValueError("non-finite JSON constant: " + value)
    return json.loads(text, parse_constant=reject)


def _missing(value):
    return value is None or isinstance(value, str) and not value.strip()


def _id(value):
    return isinstance(value, str) and bool(value.strip())


def _time(value):
    if _missing(value):
        return None, False
    if not isinstance(value, str):
        return None, True
    try:
        return datetime.fromisoformat(value), False
    except ValueError:
        return None, True


def _compare(a, b, comparison):
    if a is None or b is None or (a.tzinfo is None) != (b.tzinfo is None):
        return None
    return comparison(a, b)


def _examples(rows, field):
    return sorted({str(row[field]) for row in rows if _id(row.get(field))})[:5]


def _fingerprint(row):
    return json.dumps(row, sort_keys=True, ensure_ascii=False, default=str)


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(raw_dir, source, fallback_columns):
    rows, columns, pages = [], [], []
    try:
        if source == "orders":
            with (raw_dir / PATHS[source]).open(encoding="utf-8") as stream:
                for line_number, line in enumerate(stream, 1):
                    row = _json(line)
                    if not isinstance(row, dict):
                        raise ValueError(f"orders line {line_number} is not an object")
                    rows.append(row)
            columns = sorted({field for row in rows for field in row}) if rows else list(fallback_columns)
        elif source == "dispatch":
            pages = sorted((raw_dir / "api").glob("page_*.json"))
            if not pages:
                raise FileNotFoundError("no preserved API pages")
            for path in pages:
                envelope = _json(path.read_text(encoding="utf-8"))
                if not isinstance(envelope, dict) or not isinstance(envelope.get("data"), list):
                    raise ValueError(f"{path.name}: malformed envelope")
                if not all(isinstance(row, dict) for row in envelope["data"]):
                    raise ValueError(f"{path.name}: non-object API record")
                rows.extend(envelope["data"])
            columns = sorted({field for row in rows for field in row}) if rows else list(fallback_columns)
        else:
            with (raw_dir / PATHS[source]).open(encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream)
                columns = list(reader.fieldnames or [])
                rows = list(reader)
    except (OSError, UnicodeError, ValueError, csv.Error) as exc:
        return [], [], [], str(exc)[:300]
    return rows, columns, pages, None


def validate_run(raw_dir: Path) -> dict:
    """Profile all four raw sources, write strict JSON, and return the report."""
    run_date = raw_dir.name.removeprefix("run_date=")
    checks, profiles = [], {}

    def add(check_id, category, source, status, condition, observed, message, count=None):
        entry = {"check_id": check_id, "category": category, "source": source,
                 "status": status, "condition": condition, "observed": observed, "message": message}
        if count is not None:
            entry["affected_count"] = count
        checks.append(entry)

    manifest = {}
    try:
        manifest = _json((raw_dir / "manifest.json").read_text(encoding="utf-8"))
        if not isinstance(manifest, dict) or not isinstance(manifest.get("sources"), list):
            raise ValueError("manifest requires a sources list")
        add("raw_manifest_readable", "retrieval", "manifest", "PASS",
            "strict JSON manifest exists", {"source_entries": len(manifest["sources"])},
            "Raw manifest is readable.")
    except (OSError, UnicodeError, ValueError) as exc:
        manifest = {}
        add("raw_manifest_readable", "retrieval", "manifest", "FAIL",
            "strict JSON manifest exists", {"error": str(exc)[:300]},
            "Raw manifest is missing or malformed.")
    entries = {item["source_name"]: item for item in manifest.get("sources", [])
               if isinstance(item, dict) and isinstance(item.get("source_name"), str)}
    data, parsed, groups_by_source, pages = {}, {}, {}, []

    for source, required in REQUIRED.items():
        metadata = entries.get(source, {})
        fallback = metadata.get("columns", []) if isinstance(metadata.get("columns"), list) else []
        rows, columns, source_pages, error = _load(raw_dir, source, fallback)
        if error:
            add(source + "_raw_readable", "structural", source, "FAIL",
                "raw artifact is readable", {"error": error}, "Raw source cannot be read.")
            continue
        if source == "dispatch":
            pages = source_pages
        data[source] = rows
        add(source + "_raw_readable", "structural", source, "PASS",
            "raw artifact is readable", {"row_count": len(rows)}, "Raw source read.")
        missing_columns = sorted(set(required) - set(columns))
        add(source + "_required_columns", "structural", source,
            "FAIL" if missing_columns else "PASS", "all required columns exist",
            {"missing_columns": missing_columns}, "Schema checked without repair.", len(missing_columns))
        missing_fields = sum(any(field not in row for field in required) for row in rows)
        add(source + "_row_fields", "structural", source,
            "FAIL" if missing_fields else "PASS", "every record has required fields",
            {"rows_missing_fields": missing_fields}, "Per-record fields checked.", missing_fields)
        key = KEY[source]
        invalid_ids = sum(not _id(row.get(key)) for row in rows)
        add(source + "_key_presence", "structural", source, "FAIL" if invalid_ids else "PASS",
            f"{key} is a non-empty string", {"invalid_key_rows": invalid_ids},
            "Key presence checked without replacement.", invalid_ids)
        groups = defaultdict(list)
        for row in rows:
            if _id(row.get(key)):
                groups[row[key]].append(row)
        groups_by_source[source] = groups
        duplicates = {ident: members for ident, members in groups.items() if len(members) > 1}
        conflicting = sorted(ident for ident, members in duplicates.items()
                             if len({_fingerprint(row) for row in members}) > 1)
        exact = sorted(set(duplicates) - set(conflicting))
        if source == "dispatch":
            add("dispatch_duplicate_order_id", "structural", source,
                "FAIL" if duplicates else "PASS", "at most one dispatch record per order_id",
                {"duplicate_order_ids": len(duplicates), "examples": sorted(duplicates)[:5]},
                "Duplicate dispatch IDs would fan out an order join." if duplicates else "Dispatch IDs are unique.",
                len(duplicates))
        else:
            for suffix, identifiers, status in (("exact_duplicate_ids", exact, "WARN"),
                                                ("conflicting_duplicate_ids", conflicting, "FAIL")):
                add(source + "_" + suffix, "structural", source,
                    status if identifiers else "PASS", "reused keys are classified by full-row agreement",
                    {"duplicate_ids": len(identifiers), "examples": identifiers[:5]},
                    "Duplicate source rows are retained; no winner is selected." if identifiers else "No such duplicate keys.",
                    len(identifiers))
        times, failures = {}, {}
        for field in TIME_FIELDS[source]:
            if field not in columns:
                continue
            values = [_time(row.get(field)) for row in rows]
            times[field] = [value for value, _ in values]
            count = sum(failed for _, failed in values)
            failures[field] = count
            severity = "FAIL" if source == "orders" else "WARN"
            add(source + "_" + field + "_parse", "structural", source,
                severity if count else "PASS", f"non-null {field} parses as a timestamp",
                {"malformed_non_null": count}, "Malformed values are reported without coercion.", count)
        parsed[source] = times
        profiles[source] = {
            "row_count": len(rows), "columns": columns,
            "null_counts": {field: sum(_missing(row.get(field)) for row in rows)
                            for field in required if field in columns},
            "duplicate_key_count": len(duplicates),
            "duplicate_key_extra_rows": sum(len(members) - 1 for members in duplicates.values()),
            "unique_key_count": len(groups), "timestamp_parse_failures": failures,
        }
        for field, accepted in CATEGORIES[source].items():
            if field not in columns:
                continue
            unexpected = [row.get(field) for row in rows
                          if not isinstance(row.get(field), str) or row[field] not in accepted]
            add(source + "_" + field + "_categories", "structural", source,
                "WARN" if unexpected else "PASS", "category belongs to provisional observed vocabulary",
                {"unexpected_rows": len(unexpected),
                 "examples": sorted({str(value) for value in unexpected})[:5]},
                "Unexpected categories are retained without normalization.", len(unexpected))

    mismatches = []
    if manifest:
        for source in REQUIRED:
            metadata = entries.get(source)
            if metadata is None or source not in data:
                mismatches.append(source)
                continue
            if metadata.get("retrieved_record_count") != len(data[source]) or metadata.get("retrieval_status") != "complete":
                mismatches.append(source)
            if source in PATHS and metadata.get("raw_sha256") != _sha256(raw_dir / PATHS[source]):
                mismatches.append(source + "_hash")
        if manifest.get("run_date") != run_date:
            mismatches.append("run_date")
        add("raw_manifest_reconciliation", "retrieval", "manifest",
            "FAIL" if mismatches else "PASS", "manifest counts, status, hashes and date agree with raw artifacts",
            {"mismatches": mismatches[:10]}, "Manifest reconciled to preserved source files.", len(mismatches))
    if "dispatch" in data:
        page_errors, totals = [], []
        for number, path in enumerate(pages, 1):
            envelope = _json(path.read_text(encoding="utf-8"))
            totals.append(envelope.get("total_records"))
            if (path.name != f"page_{number:04d}.json"
                    or type(envelope.get("page")) is not int or envelope["page"] != number
                    or type(envelope.get("has_more")) is not bool
                    or envelope["has_more"] != (number < len(pages))):
                page_errors.append(path.name)
        if not totals or len(set(map(str, totals))) != 1 or type(totals[0]) is not int or totals[0] != len(data["dispatch"]):
            page_errors.append("total_records")
        if entries.get("dispatch", {}).get("pages_retrieved") != len(pages):
            page_errors.append("manifest_pages_retrieved")
        add("dispatch_raw_pagination", "retrieval", "dispatch",
            "FAIL" if page_errors else "PASS", "saved pages progress, terminate and reconcile to total",
            {"pages": len(pages), "errors": page_errors[:5]},
            "Raw HTTP pagination checked without contacting the API.", len(page_errors))

    orders = data.get("orders", [])
    order_times = parsed.get("orders", {})
    if "orders" in data:
        violations = {"orders_promise_chronology": [], "orders_milestone_chronology": [],
                      "delivered_missing_promised_eta": [], "delivered_missing_actual_delivery_at": [],
                      "orders_negative_distance": [], "orders_invalid_distance": [],
                      "orders_future_created_at": []}
        skipped = 0
        logical_date = date.fromisoformat(run_date)
        for index, row in enumerate(orders):
            def at(field):
                values = order_times.get(field, [])
                return values[index] if index < len(values) else None
            created, promised, pickup, delivered = (at(field) for field in TIME_FIELDS["orders"])
            if created is not None and created.date() > logical_date:
                violations["orders_future_created_at"].append(row)
            promise_test = _compare(promised, created, lambda a, b: a < b)
            if promise_test is True:
                violations["orders_promise_chronology"].append(row)
            elif promise_test is None and promised is not None and created is not None:
                skipped += 1
            pickup_test = _compare(pickup, created, lambda a, b: a < b)
            delivery_test = _compare(delivered, pickup, lambda a, b: a < b)
            if pickup_test is True or delivery_test is True:
                violations["orders_milestone_chronology"].append(row)
            if pickup_test is None and pickup is not None and created is not None:
                skipped += 1
            if delivery_test is None and delivered is not None and pickup is not None:
                skipped += 1
            if str(row.get("final_status", "")).strip().lower() == "delivered":
                for field, check_id in (("promised_eta", "delivered_missing_promised_eta"),
                                        ("actual_delivery_at", "delivered_missing_actual_delivery_at")):
                    if _missing(row.get(field)):
                        violations[check_id].append(row)
            value = row.get("distance_km_estimate")
            if not _missing(value):
                try:
                    distance = float(value)
                    if not math.isfinite(distance):
                        violations["orders_invalid_distance"].append(row)
                    elif distance < 0:
                        violations["orders_negative_distance"].append(row)
                except (TypeError, ValueError):
                    violations["orders_invalid_distance"].append(row)
        for check_id, bad in violations.items():
            severity = "FAIL" if check_id in {"orders_promise_chronology", "orders_milestone_chronology"} else "WARN"
            category = "lifecycle" if check_id not in {"orders_negative_distance", "orders_invalid_distance"} else "structural"
            add(check_id, category, "orders", severity if bad else "PASS",
                {"orders_promise_chronology": "promised_eta >= created_at",
                 "orders_milestone_chronology": "created_at <= pickup_at <= actual_delivery_at",
                 "delivered_missing_promised_eta": "delivered has promised_eta",
                 "delivered_missing_actual_delivery_at": "delivered has actual_delivery_at",
                 "orders_negative_distance": "distance_km_estimate >= 0",
                 "orders_invalid_distance": "distance_km_estimate is finite numeric",
                 "orders_future_created_at": "created_at is no later than logical run date"}[check_id],
                {"affected_rows": len(bad), "example_order_ids": _examples(bad, "order_id")},
                "Exceptions retained; no values changed." if bad else "Observed values satisfy this check.",
                len(bad))
        add("orders_timezone_comparison_coverage", "lifecycle", "orders",
            "WARN" if skipped else "PASS", "compared timestamps have compatible timezone awareness",
            {"skipped_comparisons": skipped}, "Mixed-awareness comparisons are not guessed.", skipped)

    order_groups = groups_by_source.get("orders", {})
    order_ids = set(order_groups)
    unambiguous = {ident: members[0] for ident, members in order_groups.items()
                   if len({_fingerprint(row) for row in members}) == 1}
    for source, time_field in (("customer_app_actions", "action_at"),
                               ("order_interventions", "intervention_at")):
        if source not in data:
            continue
        rows = data[source]
        missing_links = [row for row in rows if not _id(row.get("order_id"))]
        orphan_links = [row for row in rows if _id(row.get("order_id")) and row["order_id"] not in order_ids]
        ambiguous = sum(_id(row.get("order_id")) and row["order_id"] in order_ids
                        and row["order_id"] not in unambiguous for row in rows)
        for suffix, bad in (("missing_order_id", missing_links), ("orphan_order_id", orphan_links)):
            add(source + "_" + suffix, "cross_source", source, "WARN" if bad else "PASS",
                "child order_id is present and refers to a known order",
                {"affected_rows": len(bad), "example_child_ids": _examples(bad, KEY[source])},
                "Unlinked child rows retained." if bad else "Child links satisfy this check.", len(bad))
        add(source + "_ambiguous_parent", "cross_source", source, "UNKNOWN" if ambiguous else "PASS",
            "linked parent has no conflicting source versions", {"ambiguous_child_rows": ambiguous},
            "Conflicting parent versions prevent definitive comparisons." if ambiguous else "Linked parents are unambiguous.",
            ambiguous)
        before, after, customer_mismatch = [], [], []
        child_times = parsed.get(source, {}).get(time_field, [])
        for index, row in enumerate(rows):
            parent = unambiguous.get(row["order_id"]) if _id(row.get("order_id")) else None
            if parent is None:
                continue
            if source == "customer_app_actions" and not _missing(row.get("customer_id")) and not _missing(parent.get("customer_id")) and row["customer_id"] != parent["customer_id"]:
                customer_mismatch.append(row)
            event = child_times[index] if index < len(child_times) else None
            created = _time(parent.get("created_at"))[0]
            delivered = _time(parent.get("actual_delivery_at"))[0]
            if _compare(event, created, lambda a, b: a < b) is True:
                before.append(row)
            if _compare(event, delivered, lambda a, b: a > b) is True:
                after.append(row)
        if source == "customer_app_actions":
            add("app_customer_mismatch", "cross_source", source, "WARN" if customer_mismatch else "PASS",
                "app customer_id equals order customer_id when both exist",
                {"affected_rows": len(customer_mismatch), "example_action_ids": _examples(customer_mismatch, "action_id")},
                "Customer disagreement retained without choosing a winner.", len(customer_mismatch))
        for suffix, bad, condition in (("before_order", before, time_field + " >= created_at"),
                                        ("after_delivery", after, time_field + " <= actual_delivery_at when present")):
            add(source + "_" + suffix, "lifecycle", source, "WARN" if bad else "PASS", condition,
                {"affected_rows": len(bad), "example_child_ids": _examples(bad, KEY[source])},
                "Timing exception retained; post-order behavior may be legitimate.", len(bad))
        counts = Counter(row["order_id"] for row in rows if _id(row.get("order_id")))
        add(source + "_child_multiplicity", "cross_source", source, "PASS",
            "child source is profiled as 1:N without joining to orders",
            {"orders_with_multiple_children": sum(count > 1 for count in counts.values()),
             "maximum_children_per_order": max(counts.values(), default=0)},
            "No order journey was constructed.")

    if "dispatch" in data:
        groups = groups_by_source["dispatch"]
        orphans = [row for row in data["dispatch"] if _id(row.get("order_id")) and row["order_id"] not in order_ids]
        absent = sorted(order_ids - set(groups))
        covered = len(order_ids & set(groups))
        coverage = round(100 * covered / len(order_ids), 2) if order_ids else None
        add("dispatch_orphan_order_id", "cross_source", "dispatch", "WARN" if orphans else "PASS",
            "dispatch order_id exists in orders",
            {"affected_rows": len(orphans), "example_order_ids": _examples(orphans, "order_id")},
            "Unmatched dispatch rows retained.", len(orphans))
        add("orders_missing_dispatch", "cross_source", "dispatch", "WARN" if absent else "PASS",
            "report dispatch coverage without a fixed threshold",
            {"orders_without_dispatch": len(absent), "covered_orders": covered,
             "distinct_order_ids": len(order_ids), "coverage_percent": coverage,
             "example_order_ids": absent[:5]},
            "Dispatch coverage reported dynamically.", len(absent))
        matches = differences = missing_either = 0
        for ident in order_ids & set(groups):
            if ident not in unambiguous or len(groups[ident]) != 1:
                continue
            sql_driver = unambiguous[ident].get("driver_id")
            dispatch_driver = groups[ident][0].get("driver_id")
            if _missing(sql_driver) or _missing(dispatch_driver):
                missing_either += 1
            elif sql_driver == dispatch_driver:
                matches += 1
            else:
                differences += 1
        add("sql_dispatch_driver_consistency", "cross_source", "dispatch",
            "WARN" if differences or missing_either else "PASS",
            "historical SQL and current dispatch drivers are compared, not forced equal",
            {"matching": matches, "different": differences, "missing_either": missing_either},
            "Driver disagreement may represent reassignment rather than corruption.",
            differences + missing_either)
    if "orders" in data:
        exact = sum(len(members) > 1 and len({_fingerprint(row) for row in members}) == 1
                    for members in order_groups.values())
        conflicts = sum(len({_fingerprint(row) for row in members}) > 1 for members in order_groups.values())
        add("orders_parent_grain", "cross_source", "orders",
            "FAIL" if conflicts else "WARN" if exact else "PASS",
            "order IDs require conflict-free parent grain before modelling",
            {"unique_order_ids": len(order_groups), "exact_duplicate_ids": exact,
             "conflicting_duplicate_ids": conflicts},
            "Raw parent grain checked; no deduplication or final join occurred.", exact + conflicts)

    add("business_milestone_driver_arrival", "semantic", "selected_sources", "UNKNOWN",
        "observed driver_arrived_at_restaurant exists in selected sources", {"observed": False},
        "The selected pipeline does not contain an observed driver_arrived_at_restaurant milestone. Restaurant preparation time and driver travel/wait time therefore cannot be separated defensibly.")
    add("timestamp_timezone_definition", "semantic", "selected_sources", "UNKNOWN",
        "approved timezone contract exists", {"documented_timezone": None},
        "No timezone contract is documented; no timezone was assigned.")
    add("production_freshness_sla", "semantic", "orders", "UNKNOWN",
        "approved production freshness SLA exists", {"configured_sla": None},
        "Historical data was compared only with the logical run date; no production SLA was invented.")
    summary = {status.lower(): sum(check["status"] == status for check in checks)
               for status in ("PASS", "WARN", "FAIL", "UNKNOWN")}
    overall = "FAIL" if summary["fail"] else "WARN" if summary["warn"] or summary["unknown"] else "PASS"
    report = {"run_date": run_date, "overall_status": overall, "summary": summary,
              "profiles": profiles, "checks": checks}
    (raw_dir / "validation_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    return report
