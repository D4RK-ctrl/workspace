"""Small synthetic Phase 2 validation contracts; no classroom fixtures are mutated."""

from copy import deepcopy
import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pipeline.validate import REQUIRED, validate_run
from pipeline.extract import extract_dispatch
from run_pipeline import main


ORDER = {
    "order_id": "O1", "customer_id": "C1", "restaurant_id": "R1", "driver_id": "D1",
    "created_at": "2026-08-27T10:00:00", "promised_eta": "2026-08-27T11:00:00",
    "pickup_at": "2026-08-27T10:20:00", "actual_delivery_at": "2026-08-27T10:40:00",
    "final_status": "delivered", "city": "X", "distance_km_estimate": 1.2,
    "traffic_bucket": "low", "weather_bucket": "clear",
}
ACTION = {"action_id": "A1", "order_id": "O1", "customer_id": "C1",
          "action_type": "ETA_VIEWED", "action_at": "2026-08-27T10:10:00", "channel": "app"}
INTERVENTION = {"intervention_id": "I1", "order_id": "O1", "intervention_type": "PRIORITY_DISPATCH",
                "intervention_at": "2026-08-27T10:15:00", "initiated_by": "ops", "reason": "risk"}
DISPATCH = {"order_id": "O1", "driver_id": "D1", "original_driver_id": "D1",
            "assigned_at": "2026-08-27T10:05:00", "reassigned_at": None,
            "estimated_pickup_at": "2026-08-27T10:15:00", "current_delivery_eta": "2026-08-27T10:50:00",
            "dispatch_status": "completed", "eta_model_version": "v1"}


class ValidationTests(unittest.TestCase):
    def report(self, *, orders=None, actions=None, interventions=None, dispatch=None, run_date="2026-08-28"):
        data = {"orders": deepcopy(orders if orders is not None else [ORDER]),
                "customer_app_actions": deepcopy(actions if actions is not None else [ACTION]),
                "order_interventions": deepcopy(interventions if interventions is not None else [INTERVENTION]),
                "dispatch": deepcopy(dispatch if dispatch is not None else [DISPATCH])}
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory) / ("run_date=" + run_date)
            (raw / "sql").mkdir(parents=True)
            (raw / "files").mkdir()
            (raw / "api").mkdir()
            paths = {"orders": raw / "sql/orders.jsonl",
                     "customer_app_actions": raw / "files/customer_app_actions.csv",
                     "order_interventions": raw / "files/order_interventions.csv"}
            paths["orders"].write_text("".join(json.dumps(row) + "\n" for row in data["orders"]), encoding="utf-8")
            for source in ("customer_app_actions", "order_interventions"):
                with paths[source].open("w", encoding="utf-8", newline="") as stream:
                    writer = csv.DictWriter(stream, fieldnames=REQUIRED[source])
                    writer.writeheader()
                    writer.writerows(data[source])
            envelope = {"data": data["dispatch"], "page": 1, "page_size": 200,
                        "has_more": False, "total_records": len(data["dispatch"])}
            (raw / "api/page_0001.json").write_text(json.dumps(envelope), encoding="utf-8")
            sources = []
            for source, rows in data.items():
                item = {"source_name": source, "retrieved_record_count": len(rows),
                        "retrieval_status": "complete", "columns": list(rows[0]) if rows else list(REQUIRED[source])}
                if source in paths:
                    item["raw_sha256"] = hashlib.sha256(paths[source].read_bytes()).hexdigest()
                else:
                    item["pages_retrieved"] = 1
                sources.append(item)
            (raw / "manifest.json").write_text(json.dumps({"run_date": run_date, "sources": sources}))
            result = validate_run(raw)
            on_disk = json.loads((raw / "validation_report.json").read_text(),
                                 parse_constant=lambda value: self.fail("non-finite JSON: " + value))
            self.assertEqual(result, on_disk)
            return result

    def check(self, report, check_id, status):
        matches = [item for item in report["checks"] if item["check_id"] == check_id]
        self.assertEqual(len(matches), 1, check_id)
        self.assertEqual(matches[0]["status"], status)
        return matches[0]

    def test_missing_order_column_fails(self):
        order = deepcopy(ORDER)
        del order["promised_eta"]
        self.check(self.report(orders=[order]), "orders_required_columns", "FAIL")

    def test_conflicting_order_duplicate_fails(self):
        other = {**ORDER, "traffic_bucket": "high"}
        result = self.report(orders=[ORDER, other])
        self.check(result, "orders_conflicting_duplicate_ids", "FAIL")
        self.assertEqual(result["overall_status"], "FAIL")

    def test_exact_order_duplicate_warns(self):
        result = self.report(orders=[ORDER, ORDER])
        self.check(result, "orders_exact_duplicate_ids", "WARN")
        self.check(result, "orders_parent_grain", "WARN")

    def test_malformed_required_timestamp_fails(self):
        self.check(self.report(orders=[{**ORDER, "created_at": "nonsense"}]),
                   "orders_created_at_parse", "FAIL")

    def test_promise_before_creation_fails(self):
        self.check(self.report(orders=[{**ORDER, "promised_eta": "2026-08-27T09:00:00"}]),
                   "orders_promise_chronology", "FAIL")

    def test_pickup_after_delivery_fails(self):
        self.check(self.report(orders=[{**ORDER, "pickup_at": "2026-08-27T10:50:00"}]),
                   "orders_milestone_chronology", "FAIL")

    def test_cancelled_missing_completion_is_not_failure(self):
        result = self.report(orders=[{**ORDER, "final_status": "cancelled", "actual_delivery_at": None}])
        self.check(result, "delivered_missing_actual_delivery_at", "PASS")
        self.assertNotEqual(result["overall_status"], "FAIL")

    def test_orphan_app_order_warns(self):
        self.check(self.report(actions=[{**ACTION, "order_id": "O99"}]),
                   "customer_app_actions_orphan_order_id", "WARN")

    def test_mismatched_app_customer_warns(self):
        self.check(self.report(actions=[{**ACTION, "customer_id": "C99"}]),
                   "app_customer_mismatch", "WARN")

    def test_intervention_after_delivery_warns(self):
        self.check(self.report(interventions=[{**INTERVENTION, "intervention_at": "2026-08-27T11:00:00"}]),
                   "order_interventions_after_delivery", "WARN")

    def test_duplicate_dispatch_id_fails(self):
        result = self.report(dispatch=[DISPATCH, DISPATCH])
        self.check(result, "dispatch_duplicate_order_id", "FAIL")
        self.assertEqual(result["overall_status"], "FAIL")

    def test_missing_dispatch_id_is_preserved_then_fails_validation(self):
        malformed = {**DISPATCH, "order_id": ""}
        result = self.report(dispatch=[malformed])
        self.check(result, "dispatch_key_presence", "FAIL")
        with tempfile.TemporaryDirectory() as directory:
            body = json.dumps({"data": [malformed], "page": 1, "page_size": 200,
                               "has_more": False, "total_records": 1}).encode()
            with patch("pipeline.extract._fetch_page", return_value=body):
                evidence = extract_dispatch("http://example.invalid", 1, 1, 200, Path(directory))
            self.assertEqual(evidence["unique_order_ids"], 0)
            self.assertEqual((Path(directory) / "page_0001.json").read_bytes(), body)

    def test_driver_mismatch_warns(self):
        item = self.check(self.report(dispatch=[{**DISPATCH, "driver_id": "D2"}]),
                          "sql_dispatch_driver_consistency", "WARN")
        self.assertIn("reassignment", item["message"])

    def test_unknown_category_warns_without_normalization(self):
        item = self.check(self.report(orders=[{**ORDER, "traffic_bucket": "HIGH"}]),
                          "orders_traffic_bucket_categories", "WARN")
        self.assertEqual(item["observed"]["examples"], ["HIGH"])

    def test_future_order_warns(self):
        shifted = deepcopy(ORDER)
        for field in ("created_at", "promised_eta", "pickup_at", "actual_delivery_at"):
            shifted[field] = shifted[field].replace("2026-08-27", "2026-08-29")
        self.check(self.report(orders=[shifted]), "orders_future_created_at", "WARN")

    def test_missing_arrival_is_unknown(self):
        self.check(self.report(), "business_milestone_driver_arrival", "UNKNOWN")

    def test_unknown_alone_does_not_fail(self):
        result = self.report()
        self.assertEqual(result["summary"]["fail"], 0)
        self.assertEqual(result["summary"]["warn"], 0)
        self.assertGreater(result["summary"]["unknown"], 0)
        self.assertEqual(result["overall_status"], "WARN")

    def test_fail_has_overall_fail(self):
        result = self.report(orders=[{**ORDER, "promised_eta": "2026-08-27T09:00:00"}])
        self.assertEqual(result["overall_status"], "FAIL")
        self.assertGreater(result["summary"]["fail"], 0)

    def test_cli_exit_codes_for_validation_result(self):
        for overall, expected in (("FAIL", 2), ("WARN", 0)):
            fake = {"overall_status": overall,
                    "summary": {"pass": 1, "warn": 0, "fail": int(overall == "FAIL"), "unknown": 1}}
            with patch("sys.argv", ["run_pipeline.py", "--run-date", "2026-08-28"]), \
                 patch("run_pipeline.run", return_value=Path("data/raw/run_date=2026-08-28")), \
                 patch("run_pipeline.validate_run", return_value=fake):
                self.assertEqual(main(), expected)


if __name__ == "__main__":
    unittest.main()
