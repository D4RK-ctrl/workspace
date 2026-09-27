"""Synthetic checks for the four approved Phase 4 metric definitions."""

import csv
import json
from pathlib import Path
import tempfile
import unittest

from pipeline.metrics import MetricError, calculate_metrics, evidence_rows, read_model, write_metrics


def order(order_id, promised="2026-08-27T10:30:00", delivered="2026-08-27T10:40:00",
          pickup="2026-08-27T10:20:00", delay=True, duration=True, exposed=False):
    return {"order_id": order_id, "created_at": "2026-08-27T10:00:00",
            "promised_eta": promised, "actual_delivery_at": delivered, "pickup_at": pickup,
            "delay_metric_eligible": delay, "duration_metric_eligible": duration,
            "has_pre_delivery_intervention": exposed}


def calculate(rows):
    manifest = {"run_date": "2026-08-28", "output_order_rows": len(rows),
                "output_unique_order_ids": len(rows),
                "delay_metric_eligible_orders": sum(row["delay_metric_eligible"] is True for row in rows),
                "duration_metric_eligible_orders": sum(row["duration_metric_eligible"] is True for row in rows)}
    return calculate_metrics(rows, manifest)


class MetricTests(unittest.TestCase):
    def test_rates_medians_exclusions_and_cohorts(self):
        rows = [order("A", exposed=True), order("B", delivered="2026-08-27T10:50:00"),
                order("C", delivered="2026-08-27T10:25:00", pickup="2026-08-27T10:10:00"),
                order("D", delay=False, duration=False, delivered="bad")]
        result = calculate(rows)
        first, second, third, fourth = result["metrics"]
        self.assertEqual((first["numerator"], first["denominator"], first["value"]), (2, 3, 200 / 3))
        self.assertEqual((second["value"], second["sample_size"]), (15, 2))
        self.assertEqual((third["value"], third["sample_size"]), (20, 3))
        self.assertEqual(first["exclusions"]["not_delay_metric_eligible"], 1)
        self.assertEqual(third["exclusions"]["not_duration_metric_eligible"], 1)
        cohorts = fourth["cohort_values"]
        self.assertEqual(cohorts["exposed"], {"eligible_orders": 1, "late_orders": 1,
                                              "late_rate_percent": 100})
        self.assertEqual(cohorts["unexposed"], {"eligible_orders": 2, "late_orders": 1,
                                                "late_rate_percent": 50})
        self.assertEqual(sum(item["eligible_orders"] for item in cohorts.values()), first["denominator"])
        self.assertTrue(all(0 <= item["value"] <= 100 for item in (first,) if item["value"] is not None))
        self.assertEqual(len(evidence_rows(result)), 5)
        self.assertEqual({row["metric_id"] for row in evidence_rows(result)},
                         {"late_completed_delivery_rate", "median_lateness_minutes_among_late_orders",
                          "median_creation_to_pickup_minutes", "late_rate_intervention_exposed",
                          "late_rate_no_intervention"})

    def test_no_late_orders_has_null_median_and_zero_sample(self):
        result = calculate([order("A", delivered="2026-08-27T10:30:00")])
        self.assertIsNone(result["metrics"][1]["value"])
        self.assertEqual(result["metrics"][1]["sample_size"], 0)
        self.assertEqual(result["metrics"][0]["numerator"], 0)

    def test_invalid_eligible_timestamps_and_negative_duration_fail(self):
        for row in (order("A", promised="bad"), order("A", delivered="bad"),
                    order("A", pickup="2026-08-27T09:00:00")):
            with self.subTest(row=row), self.assertRaises(MetricError):
                calculate([row])

    def test_non_boolean_exposure_and_duplicate_id_fail(self):
        with self.assertRaises(MetricError):
            calculate([order("A", exposed="unknown")])
        with self.assertRaises(MetricError):
            calculate([order("A"), order("A")])

    def test_persisted_model_input_and_strict_outputs(self):
        rows = [order("A"), order("B", exposed=True)]
        with tempfile.TemporaryDirectory() as root:
            model_dir = Path(root) / "run_date=2026-08-28"
            model_dir.mkdir()
            with (model_dir / "order_journey.csv").open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=rows[0])
                writer.writeheader()
                writer.writerows(rows)
            manifest = {"run_date": "2026-08-28", "output_order_rows": 2,
                        "output_unique_order_ids": 2, "delay_metric_eligible_orders": 2,
                        "duration_metric_eligible_orders": 2}
            (model_dir / "model_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            persisted, loaded = read_model(model_dir)
            result = calculate_metrics(persisted, loaded)
            output = write_metrics(result, Path(root) / "gold")
            parsed = json.loads((output / "metrics.json").read_text(encoding="utf-8"),
                                parse_constant=lambda value: self.fail(f"Non-finite JSON: {value}"))
            with (output / "evidence_table.csv").open(encoding="utf-8", newline="") as stream:
                evidence = list(csv.DictReader(stream))
            self.assertEqual(len(parsed["metrics"]), 4)
            self.assertEqual(len(evidence), 5)
            self.assertEqual(sorted(path.name for path in output.iterdir()),
                             ["evidence_table.csv", "metrics.json"])


if __name__ == "__main__":
    unittest.main()
