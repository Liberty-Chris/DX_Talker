"""Bounded structured history. Raw cluster text and credentials never reach disk."""
from dataclasses import asdict
from datetime import datetime
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .models import UTC, settings_path


class History:
    def __init__(self, settings):
        self.handler = None
        self.directory = Path(settings.log_directory) if settings.log_directory else settings_path().parent / "logs"
        if settings.logging_enabled:
            self.directory.mkdir(parents=True, exist_ok=True)
            self.handler = RotatingFileHandler(self.directory / "history.jsonl", maxBytes=settings.log_max_mb * 1024 * 1024,
                                              backupCount=settings.log_backups, encoding="utf-8")
            # Match standard rotation policy even after reducing the backup setting.
            for file in self.directory.glob("history.jsonl.*"):
                suffix = file.name.rsplit(".", 1)[-1]
                if suffix.isdigit() and int(suffix) > settings.log_backups:
                    file.unlink()

    def record(self, kind, **values):
        if self.handler:
            # Call file operations directly so failures reach the UI instead of stderr.
            line = json.dumps({"schema_version": 1, "time": datetime.now(UTC).isoformat(), "kind": kind, **values}, ensure_ascii=True)
            record = logging.LogRecord("DXTalker", logging.INFO, "", 0, line, (), None)
            if self.handler.shouldRollover(record):
                self.handler.doRollover()
            self.handler.stream.write(line + "\n")
            self.handler.flush()

    def spot(self, spot, profile=""):
        values = asdict(spot)
        values.pop("comment", None)
        values.pop("mode", None)
        for key in ("frequency_khz", "timestamp", "received"):
            values[key] = str(values[key])
        self.record("spot", profile=profile, **values)

    def close(self):
        if self.handler:
            self.handler.close()
            self.handler = None
