"""Structured JSON logging for platform services."""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from praam_platform.enums import LogEvent, LogLevel


@dataclass(frozen=True)
class LogRecord:
    level: LogLevel
    message: str
    service: str
    event: LogEvent
    fields: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": self.level.value,
            "message": self.message,
            "service": self.service,
            "event": self.event.value,
        }
        payload.update(self.fields)
        return payload


class StructuredLogger:
    """Emit JSON lines or fallback to stdlib logging."""

    def __init__(
        self,
        service: str,
        *,
        json_output: bool = True,
        stream: Any = None,
    ) -> None:
        self.service = service
        self.json_output = json_output
        self.stream = stream or sys.stdout
        self._stdlib = logging.getLogger(service)

    def emit(self, record: LogRecord) -> None:
        if self.json_output:
            line = json.dumps(record.to_dict(), separators=(",", ":"), default=str)
            print(line, file=self.stream, flush=True)
            return
        extras = " ".join(f"{key}={value}" for key, value in record.fields.items())
        self._stdlib.log(
            getattr(logging, record.level.value, logging.INFO),
            "%s %s",
            record.message,
            extras,
        )

    def info(self, message: str, event: LogEvent, **fields: Any) -> None:
        self.emit(
            LogRecord(
                level=LogLevel.INFO,
                message=message,
                service=self.service,
                event=event,
                fields=fields,
            )
        )

    def http_access(
        self,
        *,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        client_ip: str = "",
    ) -> None:
        self.info(
            "request completed",
            LogEvent.HTTP_ACCESS,
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            client_ip=client_ip,
        )
