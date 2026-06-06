"""Platform dependency health checks."""

from __future__ import annotations

import socket
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from praam_platform.config import host_for_runtime, port_for_runtime
from praam_platform.enums import HealthStatus, PlatformService, Runtime


@dataclass(frozen=True)
class ServiceCheck:
    ok: bool
    target: str
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"ok": self.ok, "target": self.target}
        if self.note:
            payload["note"] = self.note
        return payload


@dataclass
class PlatformHealthReport:
    status: HealthStatus
    runtime: Runtime
    checks: dict[str, ServiceCheck] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "runtime": self.runtime.value,
            "checks": {name: check.to_dict() for name, check in self.checks.items()},
        }


class HealthProbe:
    @staticmethod
    def tcp(host: str, port: int, timeout: float) -> bool:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            return False

    @staticmethod
    def http(url: str, timeout: float) -> bool:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return 200 <= resp.status < 300
        except (urllib.error.URLError, TimeoutError, ValueError):
            return False


def check_platform_health(
    services: dict[str, Any],
    *,
    runtime: Runtime = Runtime.DOCKER,
    timeout: float = 2.0,
) -> PlatformHealthReport:
    platform = services["platform"]
    checks: dict[str, ServiceCheck] = {}

    pg = platform["postgres"]
    pg_host = host_for_runtime(runtime, pg["container_host"])
    pg_port = port_for_runtime(runtime, pg)
    checks[PlatformService.POSTGRES.value] = ServiceCheck(
        ok=HealthProbe.tcp(pg_host, pg_port, timeout),
        target=f"{pg_host}:{pg_port}",
    )

    redis = platform["redis"]
    redis_host = host_for_runtime(runtime, redis["container_host"])
    redis_port = port_for_runtime(runtime, redis)
    checks[PlatformService.REDIS.value] = ServiceCheck(
        ok=HealthProbe.tcp(redis_host, redis_port, timeout),
        target=f"{redis_host}:{redis_port}",
    )

    llm = platform["litellm"]
    llm_host = host_for_runtime(runtime, llm["container_host"])
    llm_port = port_for_runtime(runtime, llm)
    health_url = f"http://{llm_host}:{llm_port}/health/liveliness"
    checks[PlatformService.LITELLM.value] = ServiceCheck(
        ok=HealthProbe.http(health_url, timeout),
        target=health_url,
    )

    checks[PlatformService.PLATFORM_CONFIG.value] = ServiceCheck(
        ok=True,
        target="self",
        note="responding",
    )

    status = (
        HealthStatus.OK
        if all(check.ok for check in checks.values())
        else HealthStatus.DEGRADED
    )
    return PlatformHealthReport(status=status, runtime=runtime, checks=checks)
