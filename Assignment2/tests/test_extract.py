"""Focused Phase 1 tests using small temporary sources and a local HTTP server."""

from contextlib import closing
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sqlite3
import tempfile
from threading import Thread
import unittest
from urllib.parse import parse_qs, urlparse

from pipeline.config import Config
from pipeline.extract import ExtractionError, extract_csv, extract_dispatch, extract_orders
from run_pipeline import run


class DispatchServer:
    def __init__(self, records, *, fail_once_page=None, permanent_page=None):
        self.records = records
        self.fail_once_page = fail_once_page
        self.permanent_page = permanent_page
        self.calls = {}
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urlparse(self.path)
                if parsed.path == "/health":
                    self.respond(200, {"status": "ok", "service": "flasheats-dispatch-api"})
                    return
                if parsed.path != "/dispatch/orders":
                    self.respond(404, {"error": "missing"})
                    return
                query = parse_qs(parsed.query)
                page = int(query["page"][0])
                size = int(query["page_size"][0])
                outer.calls[page] = outer.calls.get(page, 0) + 1
                if page == outer.permanent_page:
                    self.respond(404, {"error": "permanent"})
                    return
                if page == outer.fail_once_page and outer.calls[page] == 1:
                    self.respond(500, {"error": "transient"})
                    return
                start = (page - 1) * size
                self.respond(200, {
                    "page": page,
                    "page_size": size,
                    "data": outer.records[start:start + size],
                    "total_records": len(outer.records),
                    "has_more": start + size < len(outer.records),
                })

            def respond(self, status, payload):
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


class ExtractionTests(unittest.TestCase):
    def test_csv_copy_is_byte_exact_and_source_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.csv"
            raw = Path(directory) / "raw.csv"
            original = b'order_id,action_type\r\nO1,"ETA, VIEWED"\r\n'
            source.write_bytes(original)
            result = extract_csv(source, raw, "customer_app_actions")
            self.assertEqual(original, source.read_bytes())
            self.assertEqual(original, raw.read_bytes())
            self.assertEqual(result["retrieved_record_count"], 1)
            self.assertEqual(result["columns"], ["order_id", "action_type"])

    def test_sql_complete_rows_and_dynamic_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "orders.db"
            with closing(sqlite3.connect(database)) as connection:
                connection.execute("CREATE TABLE orders (order_id TEXT, new_field TEXT)")
                connection.executemany("INSERT INTO orders VALUES (?, ?)", [("O1", "as-is"), ("O2", None)])
                connection.commit()
            raw = Path(directory) / "orders.jsonl"
            result = extract_orders(database, raw)
            rows = [json.loads(line) for line in raw.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(result["columns"], ["order_id", "new_field"])
            self.assertEqual(result["retrieved_record_count"], 2)
            self.assertEqual(rows, [{"order_id": "O1", "new_field": "as-is"}, {"order_id": "O2", "new_field": None}])

    def test_api_combines_multiple_pages_and_saves_each_envelope(self):
        records = [{"order_id": f"O{i}"} for i in range(5)]
        with tempfile.TemporaryDirectory() as directory, DispatchServer(records) as server:
            result = extract_dispatch(server.url, 2, 2, 2, Path(directory))
            self.assertEqual(result["retrieved_record_count"], 5)
            self.assertEqual(result["pages_retrieved"], 3)
            self.assertEqual(result["unique_order_ids"], 5)
            self.assertEqual(len(list(Path(directory).glob("page_*.json"))), 3)
            self.assertEqual(json.loads((Path(directory) / "page_0002.json").read_bytes())["data"], records[2:4])

    def test_transient_error_retried_within_bound(self):
        with tempfile.TemporaryDirectory() as directory, DispatchServer([{"order_id": "O1"}], fail_once_page=1) as server:
            result = extract_dispatch(server.url, 2, 2, 1, Path(directory))
            self.assertEqual(result["retrieved_record_count"], 1)
            self.assertEqual(server.calls[1], 2)

    def test_permanent_4xx_stops_without_retry(self):
        with tempfile.TemporaryDirectory() as directory, DispatchServer([{"order_id": "O1"}], permanent_page=1) as server:
            with self.assertRaisesRegex(ExtractionError, "permanent HTTP 404"):
                extract_dispatch(server.url, 2, 3, 1, Path(directory))
            self.assertEqual(server.calls[1], 1)

    def test_same_date_run_replaces_old_api_pages(self):
        with tempfile.TemporaryDirectory() as directory, DispatchServer([{"order_id": f"O{i}"} for i in range(3)]) as server:
            root = Path(directory)
            database = root / "data/source/database/flasheats.db"
            database.parent.mkdir(parents=True)
            with closing(sqlite3.connect(database)) as connection:
                connection.execute("CREATE TABLE orders (order_id TEXT)")
                connection.execute("INSERT INTO orders VALUES ('O1')")
                connection.commit()
            files = root / "data/source/files"
            files.mkdir(parents=True)
            (files / "customer_app_actions.csv").write_text("action_id,order_id\nA1,O1\n")
            (files / "order_interventions.csv").write_text("intervention_id,order_id\nI1,O1\n")
            config = Config(root, date(2026, 8, 28), server.url, 2, 2, 2)
            result_dir = run(config)
            self.assertEqual(len(list((result_dir / "api").glob("page_*.json"))), 2)
            server.records = [{"order_id": "O1"}]
            run(config)
            self.assertEqual([p.name for p in (result_dir / "api").glob("page_*.json")], ["page_0001.json"])
            self.assertEqual(json.loads((result_dir / "manifest.json").read_text())["sources"][3]["retrieved_record_count"], 1)


if __name__ == "__main__":
    unittest.main()
