"""Local publication and rollback tests with tiny synthetic artifacts."""

import csv
import json
import logging
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pipeline.publish import (EXPECTED_METRIC_IDS, PublicationError, new_run_id, publish_attempt, sha256,
                              verify_artifacts, write_json)


RUN_DATE = "2026-08-28"


def artifact_dirs(root, marker):
    output = {stage: root / stage / f"run_date={RUN_DATE}" for stage in ("raw", "processed", "gold")}
    for directory in output.values():
        directory.mkdir(parents=True)
    write_json(output["raw"] / "manifest.json", {"run_date": RUN_DATE, "marker": marker})
    write_json(output["raw"] / "validation_report.json", {"summary": {"warn": 0}})
    (output["raw"] / "page_0001.json").write_text(marker, encoding="utf-8")
    with (output["processed"] / "order_journey.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["order_id", "marker"])
        writer.writeheader()
        writer.writerow({"order_id": "A", "marker": marker})
    write_json(output["processed"] / "model_manifest.json",
               {"run_date": RUN_DATE, "output_order_rows": 1, "output_unique_order_ids": 1})
    write_json(output["gold"] / "metrics.json",
               {"run_date": RUN_DATE, "metrics": [{"metric_id": name} for name in sorted(EXPECTED_METRIC_IDS)]})
    with (output["gold"] / "evidence_table.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["metric_id"])
        writer.writeheader()
        writer.writerows({"metric_id": str(i)} for i in range(5))
    return output


def attempt_manifest(run_id):
    return {"run_id": run_id, "run_date": RUN_DATE, "stages": {
        "publish": {"status": "RUNNING", "started_at": "now", "completed_at": None, "message": ""}}}


class PublicationTests(unittest.TestCase):
    def test_replacement_hashes_strict_manifest_and_no_appended_pages(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            project_root = base / "project"
            old = artifact_dirs(project_root / "data", "old")
            staged = artifact_dirs(base / "attempt", "new")
            old["raw"].joinpath("page_0002.json").write_text("stale", encoding="utf-8")
            latest = project_root / "data" / "run_manifest.json"
            write_json(latest, {"run_id": "old"})
            attempt_file = base / "attempt" / "run_manifest.json"
            result = publish_attempt(staged, old, latest, attempt_file,
                                     attempt_manifest("new"), logging.getLogger("test_publish"))
            self.assertEqual(json.loads(latest.read_text())["run_id"], "new")
            self.assertEqual(result["overall_status"], "SUCCESS")
            self.assertEqual(sorted(path.name for path in old["raw"].glob("page_*.json")),
                             ["page_0001.json"])
            checked = verify_artifacts(old, RUN_DATE)
            self.assertEqual(checked["order_count"], 1)
            self.assertEqual(checked["evidence_count"], 5)
            self.assertEqual(len(checked["metrics"]["metrics"]), 4)
            for key, path in checked["paths"].items():
                self.assertEqual(result["artifact_sha256"][key], sha256(path))
                location = result["artifact_locations"][key]
                self.assertFalse(Path(location).is_absolute())
                self.assertEqual(location, path.relative_to(project_root).as_posix())
                self.assertEqual((project_root / location).resolve(), path.resolve())
            self.assertEqual(result["artifact_locations"],
                             json.loads(latest.read_text())["artifact_locations"])
            self.assertEqual(json.loads(attempt_file.read_text(),
                                        parse_constant=lambda value: self.fail(value))["run_id"], "new")

    def test_publication_failure_restores_old_directories_and_latest_manifest(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            old = artifact_dirs(base / "project" / "data", "old")
            staged = artifact_dirs(base / "attempt", "new")
            latest = base / "project" / "data" / "run_manifest.json"
            write_json(latest, {"run_id": "old"})
            real_replace = os.replace

            def fail_gold(source, target):
                if Path(source) == staged["gold"] and Path(target) == old["gold"]:
                    raise OSError("synthetic gold rename failure")
                return real_replace(source, target)

            with patch("pipeline.publish.os.replace", side_effect=fail_gold):
                with self.assertRaises(PublicationError):
                    publish_attempt(staged, old, latest, base / "attempt" / "run_manifest.json",
                                    attempt_manifest("new"), logging.getLogger("test_publish"))
            self.assertEqual(json.loads(latest.read_text())["run_id"], "old")
            self.assertEqual(json.loads((old["raw"] / "manifest.json").read_text())["marker"], "old")
            self.assertEqual(json.loads((old["gold"] / "metrics.json").read_text())["run_date"], RUN_DATE)
            self.assertEqual(json.loads((staged["raw"] / "manifest.json").read_text())["marker"], "new")
            self.assertTrue(staged["gold"].exists())

    def test_run_ids_are_unique(self):
        self.assertNotEqual(new_run_id(), new_run_id())


if __name__ == "__main__":
    unittest.main()
