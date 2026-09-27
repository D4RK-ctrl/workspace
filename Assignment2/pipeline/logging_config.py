"""Attempt-scoped structured pipeline logging."""

import logging
from pathlib import Path


def configure_logging(attempt_dir: Path, run_id: str, run_date: str) -> logging.Logger:
    log_path = attempt_dir / "logs" / "pipeline.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("flasheats")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s run_id=" + run_id + " run_date=" + run_date + " %(message)s"))
    logger.addHandler(handler)
    return logger
