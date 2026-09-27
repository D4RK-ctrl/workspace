"""Synthetic tests for order-grain joins, child aggregates and readiness gating."""

from copy import deepcopy
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pipeline.transform import ModelError, _left_join, build_model, write_model
from run_pipeline import main, unhandled_validation_failures
from test_clean import ORDER


ACTION = {"action_id": "A1", "order_id": "O1", "customer_id": "C1",
          "action_type": "ETA_VIEWED", "action_at": "2026-08-27T10:10:00", "channel": "app"}
INTERVENTION = {"intervention_id": "I1", "order_id": "O1", "intervention_type": "PRIORITY_DISPATCH",
                "intervention_at": "2026-08-27T10:15:00", "initiated_by": "ops", "reason": "risk"}
DISPATCH = {"order_id": "O1", "driver_id": "D2", "original_driver_id": "D1",
            "assigned_at": "2026-08-27T10:05:00", "reassigned_at": "2026-08-27T10:12:00",
            "estimated_pickup_at": "2026-08-27T10:18:00", "current_delivery_eta": "2026-08-27T10:50:00",
            "dispatch_status": "completed", "eta_model_version": "v1"}


def input_sources(**overrides):
    raw = {"orders": [deepcopy(ORDER)], "customer_app_actions": [deepcopy(ACTION)],
           "order_interventions": [deepcopy(INTERVENTION)], "dispatch": [deepcopy(DISPATCH)]}
    raw.update(overrides)
    return raw


def validation(*fail_ids):
    return {"overall_status": "FAIL" if fail_ids else "WARN",
            "summary": {"pass": 1, "warn": 0, "fail": len(fail_ids), "unknown": 1},
            "checks": [{"check_id": ident, "status": "FAIL"} for ident in fail_ids]}


class TransformTests(unittest.TestCase):
    def model(self, **sources):
        return build_model(input_sources(**sources), "2026-08-28", validation())

    def test_three_actions_aggregate_without_fanout_and_count_post_delivery(self):
        actions = [ACTION, {**ACTION, "action_id": "A2", "action_type": "SUPPORT_OPENED",
                            "action_at": "2026-08-27T10:30:00"},
                   {**ACTION, "action_id": "A3", "action_type": "CANCEL_ATTEMPTED",
                    "action_at": "2026-08-27T11:00:00"}]
        journey, manifest = self.model(customer_app_actions=actions)
        self.assertEqual(len(journey), 1)
        row = journey[0]
        self.assertEqual([row[field] for field in ("app_action_count_total", "eta_viewed_count",
                                                    "support_opened_count", "cancel_attempted_count")], [3, 1, 1, 1])
        self.assertEqual((row["pre_delivery_action_count"], row["post_delivery_action_count"]), (2, 1))
        self.assertEqual(manifest["join_row_count_checks"][0]["rows_after"], 1)

    def test_multiple_interventions_aggregate_and_post_delivery_is_not_rescue(self):
        interventions = [INTERVENTION,
                         {**INTERVENTION, "intervention_id": "I2", "intervention_type": "CUSTOMER_CREDIT",
                          "intervention_at": "2026-08-27T11:00:00"},
                         {**INTERVENTION, "intervention_id": "I3", "intervention_type": "RESTAURANT_CONTACT",
                          "intervention_at": "2026-08-27T09:00:00"}]
        journey, _ = self.model(order_interventions=interventions)
        row = journey[0]
        self.assertEqual(len(journey), 1)
        self.assertEqual(row["intervention_count_total"], 3)
        self.assertEqual((row["pre_delivery_intervention_count"],
                          row["post_delivery_intervention_count"],
                          row["unclassified_intervention_count"]), (1, 1, 1))
        self.assertTrue(row["has_pre_delivery_intervention"])
        self.assertEqual(row["customer_credit_count"], 1)

    def test_missing_delivery_makes_intervention_timing_unclassified(self):
        journey, _ = self.model(orders=[{**ORDER, "actual_delivery_at": None}])
        row = journey[0]
        self.assertEqual(row["unclassified_intervention_count"], 1)
        self.assertEqual(row["pre_delivery_intervention_count"], 0)
        self.assertFalse(row["has_pre_delivery_intervention"])

    def test_dispatch_driver_columns_are_distinct_and_join_preserves_grain(self):
        journey, manifest = self.model()
        row = journey[0]
        self.assertEqual((row["sql_driver_id"], row["dispatch_driver_id"],
                          row["dispatch_original_driver_id"]), ("D1", "D2", "D1"))
        self.assertTrue(row["driver_assignment_changed"])
        self.assertEqual(row["promised_eta"], ORDER["promised_eta"])
        self.assertEqual(row["dispatch_current_delivery_eta"], DISPATCH["current_delivery_eta"])
        self.assertTrue(all(check["parent_grain_preserved"] for check in manifest["join_row_count_checks"]))

    def test_duplicate_dispatch_fails_model_construction(self):
        with self.assertRaisesRegex(ModelError, "Dispatch requires a unique"):
            self.model(dispatch=[DISPATCH, DISPATCH])

    def test_child_rows_cannot_fan_out_the_parent(self):
        children = [{"order_id": "O1", "n": 1}, {"order_id": "O1", "n": 2}]
        with self.assertRaisesRegex(ModelError, "more than one aggregate row"):
            _left_join([{"order_id": "O1"}], children, "bad_child", {"n": 0})

    def test_conflicting_parent_excluded_and_manifest_matches_unique_output(self):
        second = {**ORDER, "order_id": "O2"}
        conflict = {**second, "traffic_bucket": "medium"}
        journey, manifest = self.model(orders=[ORDER, second, conflict])
        self.assertEqual([row["order_id"] for row in journey], ["O1"])
        self.assertEqual(manifest["conflicting_order_ids"], 1)
        self.assertEqual(manifest["excluded_conflicting_order_ids"][0]["order_id"], "O2")
        self.assertEqual(manifest["output_order_rows"], manifest["output_unique_order_ids"])

    def test_multiple_children_and_missing_child_rows_keep_unique_order_ids(self):
        second = {**ORDER, "order_id": "O2"}
        actions = [ACTION, {**ACTION, "action_id": "A2"}, {**ACTION, "action_id": "A3"}]
        journey, manifest = self.model(orders=[ORDER, second], customer_app_actions=actions)
        self.assertEqual(len(journey), 2)
        self.assertEqual(len({row["order_id"] for row in journey}), 2)
        self.assertEqual(journey[1]["app_action_count_total"], 0)
        self.assertEqual([check["rows_after"] for check in manifest["join_row_count_checks"]], [2, 2, 2])

    def test_unhandled_fail_blocks_and_only_four_ids_are_approved(self):
        approved = ("orders_conflicting_duplicate_ids", "orders_parent_grain",
                    "orders_promise_chronology", "orders_milestone_chronology")
        self.assertEqual(unhandled_validation_failures(validation(*approved)), [])
        self.assertEqual(unhandled_validation_failures(validation(*approved, "dispatch_duplicate_order_id")),
                         ["dispatch_duplicate_order_id"])
        with self.assertRaisesRegex(ModelError, "Unhandled validation FAIL"):
            build_model(input_sources(), "2026-08-28", validation("dispatch_duplicate_order_id"))
        self.assertEqual(unhandled_validation_failures({"overall_status": "FAIL", "checks": []}),
                         ["unexplained_validation_fail"])

    def test_cli_does_not_call_model_on_unhandled_fail(self):
        report = validation("dispatch_duplicate_order_id")
        with patch("sys.argv", ["run_pipeline.py", "--run-date", "2026-08-28"]), \
             patch("run_pipeline.run", return_value=Path("data/raw/run_date=2026-08-28")), \
             patch("run_pipeline.validate_run", return_value=report), \
             patch("run_pipeline.read_raw_artifacts") as read_raw, \
             patch("run_pipeline.read_model") as read_model:
            self.assertEqual(main(), 2)
            read_raw.assert_not_called()
            read_model.assert_not_called()

    def test_cli_approved_fails_can_build_model(self):
        approved = ("orders_conflicting_duplicate_ids", "orders_parent_grain",
                    "orders_promise_chronology", "orders_milestone_chronology")
        with patch("sys.argv", ["run_pipeline.py", "--run-date", "2026-08-28"]), \
             patch("run_pipeline.run", return_value=Path("data/raw/run_date=2026-08-28")), \
             patch("run_pipeline.validate_run", return_value=validation(*approved)), \
             patch("run_pipeline.read_raw_artifacts", return_value=input_sources()), \
             patch("run_pipeline.write_model", return_value=Path("data/processed/run_date=2026-08-28")), \
             patch("run_pipeline.read_model", return_value=([], {})) as read_model, \
             patch("run_pipeline.calculate_metrics", return_value={"metrics": [
                 {"metric_id": name, "value": None} for name in ("late_completed_delivery_rate",
                 "median_lateness_minutes_among_late_orders", "median_creation_to_pickup_minutes")]}), \
             patch("run_pipeline.write_metrics", return_value=Path("data/gold/run_date=2026-08-28")) as write_metrics:
            self.assertEqual(main(), 0)
            read_model.assert_called_once()
            write_metrics.assert_called_once()

    def test_written_model_has_unique_ids_and_strict_json_manifest(self):
        journey, manifest = self.model()
        with tempfile.TemporaryDirectory() as directory:
            output = write_model(journey, manifest, Path(directory))
            with (output / "order_journey.csv").open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
            loaded = json.loads((output / "model_manifest.json").read_text(encoding="utf-8"),
                                parse_constant=lambda value: self.fail("non-finite JSON: " + value))
            self.assertEqual(len(rows), len({row["order_id"] for row in rows}))
            self.assertEqual(loaded["output_order_rows"], len(rows))
            self.assertEqual(sorted(path.name for path in output.iterdir()),
                             ["model_manifest.json", "order_journey.csv"])


if __name__ == "__main__":
    unittest.main()
