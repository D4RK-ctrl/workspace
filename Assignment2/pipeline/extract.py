"""Retrieval and raw evidence for exactly four Phase 1 logical sources."""

import csv
from contextlib import closing
import hashlib
import json
import logging
import math
from pathlib import Path
import shutil
import sqlite3
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


TRANSIENT_STATUSES = {429, 500, 502, 503, 504}


class ExtractionError(RuntimeError):
    """Retrieval or completeness could not be established."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_orders(database: Path, artifact: Path) -> dict:
    """Read all SQL rows without business-value changes; preserve NULLs in JSON Lines."""
    if not database.is_file():
        raise ExtractionError(f"SQLite source missing: {database}")
    artifact.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    try:
        with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
            cursor = connection.execute("SELECT * FROM orders")
            columns = [item[0] for item in cursor.description]
            with artifact.open("w", encoding="utf-8", newline="") as output:
                for batch in iter(lambda: cursor.fetchmany(1000), []):
                    for row in batch:
                        output.write(json.dumps(dict(zip(columns, row)), ensure_ascii=False, allow_nan=False) + "\n")
                    count += len(batch)
    except sqlite3.Error as exc:
        raise ExtractionError(f"SQLite orders retrieval failed: {exc}") from exc
    return {
        "source_name": "orders",
        "retrieval_mode": "sqlite",
        "source_location": "data/source/database/flasheats.db#orders",
        "table": "orders",
        "retrieved_record_count": count,
        "columns": columns,
        "raw_artifact": "sql/orders.jsonl",
        "raw_sha256": _sha256(artifact),
        "retrieval_status": "complete",
        "completeness_evidence": "SELECT * cursor exhausted",
    }


def extract_csv(source: Path, artifact: Path, source_name: str) -> dict:
    """Copy original bytes, then count CSV records in the preserved copy."""
    if not source.is_file():
        raise ExtractionError(f"CSV source missing: {source}")
    artifact.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, artifact)
    try:
        with artifact.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream)
            columns = next(reader)
            count = sum(1 for _ in reader)
    except (UnicodeError, csv.Error, StopIteration) as exc:
        raise ExtractionError(f"CSV retrieval failed for {source_name}: {exc}") from exc
    return {
        "source_name": source_name,
        "retrieval_mode": "csv_file",
        "source_location": f"data/source/files/{source.name}",
        "retrieved_record_count": count,
        "columns": columns,
        "raw_artifact": f"files/{source.name}",
        "raw_sha256": _sha256(artifact),
        "retrieval_status": "complete",
        "completeness_evidence": "copied source bytes; CSV reader reached end of file",
    }


def _bounded_wait(attempt: int, response: HTTPError | None) -> float:
    """Honor a valid small Retry-After; otherwise use bounded backoff."""
    candidate = None
    if response is not None:
        candidate = response.headers.get("Retry-After")
        if candidate is None and response.code == 429:
            try:
                candidate = json.loads(response.read()).get("retry_after_seconds")
            except (ValueError, AttributeError, UnicodeError):
                pass
    try:
        seconds = float(candidate)
        if math.isfinite(seconds) and seconds >= 0:
            return min(seconds, 3.0)
    except (TypeError, ValueError):
        pass
    return min(0.25 * 2 ** (attempt - 1), 3.0)


def _fetch_page(url: str, timeout: float, max_retries: int, page: int) -> bytes:
    for attempt in range(1, max_retries + 1):
        try:
            with urlopen(Request(url, headers={"Accept": "application/json"}), timeout=timeout) as response:
                if response.status != 200:
                    raise ExtractionError(f"Dispatch page {page}: unexpected HTTP {response.status}")
                return response.read()
        except HTTPError as exc:
            if exc.code not in TRANSIENT_STATUSES:
                raise ExtractionError(f"Dispatch page {page}: permanent HTTP {exc.code}") from exc
            reason = f"HTTP {exc.code}"
            retry_after = exc
        except (URLError, TimeoutError) as exc:
            reason = str(exc)
            retry_after = None
        if attempt == max_retries:
            raise ExtractionError(f"Dispatch page {page}: {reason}; exhausted {max_retries} attempts")
        wait = _bounded_wait(attempt, retry_after)
        message = f"retry page={page} attempt={attempt}/{max_retries} reason={reason} wait={wait:g}s"
        logging.getLogger("flasheats").warning("api %s", message)
        print(f"[API] {message}")
        time.sleep(wait)
    raise AssertionError("unreachable retry loop")


def extract_dispatch(api_url: str, timeout: float, max_retries: int, page_size: int, artifact_dir: Path) -> dict:
    """Fetch every HTTP page; save its exact body before interpreting the envelope."""
    artifact_dir.mkdir(parents=True, exist_ok=True)
    endpoint = api_url.rstrip("/") + "/dispatch/orders"
    page = 1
    total = None
    received = 0
    seen_ids = set()
    while True:
        url = endpoint + "?" + urlencode({"page": page, "page_size": page_size})
        body = _fetch_page(url, timeout, max_retries, page)
        (artifact_dir / f"page_{page:04d}.json").write_bytes(body)
        try:
            envelope = json.loads(body)
        except (ValueError, UnicodeError) as exc:
            raise ExtractionError(f"Dispatch page {page}: invalid JSON") from exc
        if not isinstance(envelope, dict):
            raise ExtractionError(f"Dispatch page {page}: envelope is not an object")
        rows = envelope.get("data")
        reported = envelope.get("total_records")
        has_more = envelope.get("has_more")
        returned_page = envelope.get("page")
        returned_size = envelope.get("page_size")
        if (type(returned_page) is not int or returned_page != page
                or type(returned_size) is not int or returned_size != page_size
                or type(reported) is not int or reported < 0
                or type(has_more) is not bool or not isinstance(rows, list)):
            raise ExtractionError(f"Dispatch page {page}: malformed pagination metadata")
        if total is None:
            total = reported
        elif reported != total:
            raise ExtractionError(f"Dispatch page {page}: total_records changed from {total} to {reported}")
        if len(rows) > page_size or (has_more and not rows):
            raise ExtractionError(f"Dispatch page {page}: no progress or oversized page")
        for row in rows:
            if not isinstance(row, dict):
                raise ExtractionError(f"Dispatch page {page}: record is not a JSON object")
            order_id = row.get("order_id")
            if isinstance(order_id, str) and order_id.strip():
                seen_ids.add(order_id)
        received += len(rows)
        if received > total:
            raise ExtractionError(f"Dispatch page {page}: received {received} exceeds reported total {total}")
        if not has_more:
            if received != total:
                raise ExtractionError(f"Dispatch ended with {received} records; reported total {total}")
            break
        if received == total:
            raise ExtractionError(f"Dispatch page {page}: has_more true after reported total reached")
        page += 1
        if page > total + 1:
            raise ExtractionError("Dispatch pagination exceeded maximum possible page count")
    return {
        "source_name": "dispatch",
        "retrieval_mode": "http_api",
        "source_location": endpoint,
        "retrieved_record_count": received,
        "columns": sorted({key for file in sorted(artifact_dir.glob("page_*.json"))
                           for row in json.loads(file.read_bytes())["data"] for key in row}),
        "raw_artifact": "api/",
        "retrieval_status": "complete",
        "pages_retrieved": page,
        "reported_total_records": total,
        "unique_order_ids": len(seen_ids),
        "completeness_evidence": {
            "page_progression": f"1..{page}",
            "has_more_terminated": True,
            "received_equals_reported_total": received == total,
            "order_ids_unique": len(seen_ids) == received,
        },
    }
