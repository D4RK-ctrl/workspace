"""Synthetic tests for conservative order-parent preparation."""

from copy import deepcopy
import unittest

from pipeline.clean import prepare_orders


ORDER = {
    "order_id": "O1", "customer_id": "C1", "restaurant_id": "R1", "driver_id": "D1",
    "created_at": "2026-08-27T10:00:00", "promised_eta": "2026-08-27T11:00:00",
    "pickup_at": "2026-08-27T10:20:00", "actual_delivery_at": "2026-08-27T10:40:00",
    "final_status": "Delivered", "traffic_bucket": "HIGH", "weather_bucket": " Clear ",
    "city": "X", "distance_km_estimate": 1.2,
}


class CleanTests(unittest.TestCase):
    def test_unique_order_yields_one_parent(self):
        rows, stats = prepare_orders([deepcopy(ORDER)])
        self.assertEqual(len(rows), 1)
        self.assertEqual(stats["input_unique_order_ids"], 1)
        self.assertEqual(rows[0]["order_id"], "O1")

    def test_exact_duplicate_collapses_with_provenance(self):
        rows, stats = prepare_orders([deepcopy(ORDER), deepcopy(ORDER)])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source_order_row_count"], 2)
        self.assertTrue(rows[0]["exact_duplicate_collapsed"])
        self.assertEqual(stats["exact_duplicate_order_ids"], 1)
        self.assertEqual(stats["exact_duplicate_ids"], ["O1"])

    def test_conflicting_duplicate_excluded_entirely_and_recorded(self):
        conflict = {**ORDER, "traffic_bucket": "medium"}
        rows, stats = prepare_orders([deepcopy(ORDER), conflict])
        self.assertEqual(rows, [])
        self.assertEqual(stats["conflicting_order_ids"], 1)
        self.assertEqual(stats["excluded_conflicting_order_ids"], [{
            "order_id": "O1", "source_row_count": 2, "model_excluded": True,
            "model_exclusion_reason": "conflicting_order_versions",
        }])

    def test_impossible_chronology_retained_but_ineligible_for_delay(self):
        invalid = {**ORDER, "promised_eta": "2026-08-27T09:00:00"}
        rows, _ = prepare_orders([invalid])
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0]["chronology_valid"])
        self.assertFalse(rows[0]["delay_metric_eligible"])
        self.assertTrue(rows[0]["duration_metric_eligible"])

    def test_missing_delivery_remains_null_and_ineligible(self):
        rows, _ = prepare_orders([{**ORDER, "actual_delivery_at": None}])
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]["actual_delivery_at"])
        self.assertTrue(rows[0]["chronology_valid"])
        self.assertFalse(rows[0]["delay_metric_eligible"])

    def test_case_and_whitespace_normalization_keeps_original_values(self):
        rows, _ = prepare_orders([deepcopy(ORDER)])
        row = rows[0]
        self.assertEqual((row["final_status_raw"], row["final_status_norm"]), ("Delivered", "delivered"))
        self.assertEqual((row["traffic_bucket_raw"], row["traffic_bucket_norm"]), ("HIGH", "high"))
        self.assertEqual((row["weather_bucket_raw"], row["weather_bucket_norm"]), (" Clear ", "clear"))
        self.assertEqual(row["promised_eta"], ORDER["promised_eta"])


if __name__ == "__main__":
    unittest.main()
