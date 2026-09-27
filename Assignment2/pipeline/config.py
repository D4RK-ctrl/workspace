"""Small, typed configuration for the Phase 1 extraction command."""

from dataclasses import dataclass
from datetime import date
import os
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class Config:
    project_root: Path
    run_date: date
    api_url: str
    api_timeout_seconds: float
    api_max_retries: int
    api_page_size: int

    @property
    def source_root(self) -> Path:
        return self.project_root / "data" / "source"

    @property
    def raw_root(self) -> Path:
        return self.project_root / "data" / "raw"

    @classmethod
    def from_environment(cls, project_root: Path, run_date: date) -> "Config":
        api_url = os.environ.get("DISPATCH_API_URL", "http://127.0.0.1:8000").rstrip("/")
        parsed = urlparse(api_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("DISPATCH_API_URL must be an HTTP(S) base URL")

        timeout = float(os.environ.get("API_TIMEOUT_SECONDS", "5"))
        retries = int(os.environ.get("API_MAX_RETRIES", "3"))
        page_size = int(os.environ.get("API_PAGE_SIZE", "200"))
        if not 0 < timeout <= 60:
            raise ValueError("API_TIMEOUT_SECONDS must be greater than 0 and at most 60")
        if not 1 <= retries <= 10:
            raise ValueError("API_MAX_RETRIES must be between 1 and 10")
        if not 1 <= page_size <= 200:
            raise ValueError("API_PAGE_SIZE must be between 1 and 200")
        return cls(project_root.resolve(), run_date, api_url, timeout, retries, page_size)
