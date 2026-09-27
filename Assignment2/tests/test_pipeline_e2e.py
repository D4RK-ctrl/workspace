"""Attempt orchestration with synthetic model input and real metric/publication code."""

from contextlib import redirect_stderr, redirect_stdout
from datetime import date
import io
import json
import logging
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pipeline.config import Config
from pipeline.metrics import MetricError
from pipeline.publish import sha256, write_json
from pipeline.transform import ModelError
from run_pipeline import main


RUN_DATE = "2026-08-28"
ROW = {"order_id": "A", "created_at": "2026-08-27T10:00:00",
       "promised_eta": "2026-08-27T10:30:00", "pickup_at": "2026-08-27T10:20:00",
       "actual_delivery_at": "2026-08-27T10:40:00", "delay_metric_eligible": True,
       "duration_metric_eligible": True, "has_pre_delivery_intervention": False}
MODEL = {"run_date": RUN_DATE, "output_order_rows": 1, "output_unique_order_ids": 1,
         "conflicting_order_ids": 0, "delay_metric_eligible_orders": 1,
         "duration_metric_eligible_orders": 1}
REPORT = {"overall_status": "WARN", "summary": {"pass": 1, "warn": 0, "fail": 0, "unknown": 1},
          "checks": []}


class PipelineAttemptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = Config(self.root, date.fromisoformat(RUN_DATE), "http://127.0.0.1:8000", 1, 1, 200)

    def tearDown(self):
        logger = logging.getLogger("flasheats")
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()

    def fake_run(self, config, raw_root):
        directory = raw_root / f"run_date={RUN_DATE}"
        directory.mkdir(parents=True)
        write_json(directory / "manifest.json", {"run_date": RUN_DATE, "sources": []})
        (directory / "page_0001.json").write_text("one page", encoding="utf-8")
        return directory

    def fake_validate(self, directory, report=REPORT):
        write_json(directory / "validation_report.json", report)
        return report

    def invoke(self, validate=None, model=None, calculate=None):
        patches = [patch("sys.argv", ["run_pipeline.py", "--run-date", RUN_DATE]),
                   patch("run_pipeline.Config.from_environment", return_value=self.config),
                   patch("run_pipeline.run", side_effect=self.fake_run),
                   patch("run_pipeline.validate_run", side_effect=validate or self.fake_validate),
                   patch("run_pipeline.read_raw_artifacts", return_value={}),
                   patch("run_pipeline.build_model", side_effect=model or (lambda *args: ([ROW], MODEL)))]
        if calculate is not None:
            patches.append(patch("run_pipeline.calculate_metrics", side_effect=calculate))
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            entered = []
            try:
                for item in patches:
                    entered.append(item)
                    item.__enter__()
                return main()
            finally:
                for item in reversed(entered):
                    item.__exit__(None, None, None)

    def latest(self):
        return json.loads((self.root / "data" / "run_manifest.json").read_text(encoding="utf-8"))

    def test_successful_rerun_is_deterministic_and_logs_attempts(self):
        self.assertEqual(self.invoke(), 0)
        first = self.latest()
        public = self.root / "data"
        artifact_paths = [public / stage / f"run_date={RUN_DATE}" / name for stage, name in (
            ("raw", "manifest.json"), ("raw", "validation_report.json"),
            ("processed", "order_journey.csv"), ("processed", "model_manifest.json"),
            ("gold", "metrics.json"), ("gold", "evidence_table.csv"))]
        first_hashes = [sha256(path) for path in artifact_paths]
        (public / "raw" / f"run_date={RUN_DATE}" / "page_9999.json").write_text("stale", encoding="utf-8")
        self.assertEqual(self.invoke(), 0)
        second = self.latest()
        self.assertNotEqual(first["run_id"], second["run_id"])
        self.assertEqual(first_hashes, [sha256(path) for path in artifact_paths])
        self.assertEqual(len(list((public / "raw" / f"run_date={RUN_DATE}").glob("page_*.json"))), 1)
        self.assertEqual(len(list((public / "gold" / f"run_date={RUN_DATE}").glob("*.csv"))), 1)
        self.assertEqual(first["metric_ids"], second["metric_ids"])
        self.assertEqual(len(second["metric_ids"]), 4)
        for run_id in (first["run_id"], second["run_id"]):
            log = public / ".runs" / run_id / "logs" / "pipeline.log"
            self.assertTrue(log.is_file())
            body = log.read_text(encoding="utf-8")
            self.assertIn(run_id, body)
            self.assertIn("stage=publish", body)
        for key, path in second["artifact_locations"].items():
            self.assertEqual(second["artifact_sha256"][key], sha256(Path(path)))
        metric = json.loads(artifact_paths[4].read_text(encoding="utf-8"))
        self.assertEqual(metric["metrics"][0]["value"], 100)
        self.assertEqual(metric["metrics"][1]["value"], 10)

    def test_failed_validation_model_or_metrics_preserves_prior_publication(self):
        self.assertEqual(self.invoke(), 0)
        latest_path = self.root / "data" / "run_manifest.json"
        gold_path = self.root / "data" / "gold" / f"run_date={RUN_DATE}" / "metrics.json"
        before = (latest_path.read_bytes(), gold_path.read_bytes())
        blocked = {"overall_status": "FAIL", "summary": {"pass": 0, "warn": 0, "fail": 1, "unknown": 0},
                   "checks": [{"check_id": "unhandled_test_failure", "status": "FAIL"}]}
        for expected, options in ((2, {"validate": lambda directory: self.fake_validate(directory, blocked)}),
                                  (3, {"model": lambda *args: (_ for _ in ()).throw(ModelError("synthetic"))}),
                                  (4, {"calculate": lambda *args: (_ for _ in ()).throw(MetricError("synthetic"))})):
            with self.subTest(exit_code=expected):
                self.assertEqual(self.invoke(**options), expected)
                self.assertEqual((latest_path.read_bytes(), gold_path.read_bytes()), before)
        failed = [json.loads(path.read_text()) for path in
                  (self.root / "data" / ".runs").glob("*/run_manifest.json")
                  if json.loads(path.read_text())["overall_status"] == "FAILED"]
        self.assertEqual({item["exit_code"] for item in failed}, {2, 3, 4})


if __name__ == "__main__":
    unittest.main()
