from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
import socket
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _default_instance_id() -> str:
    seed = f"{socket.gethostname()}:{Path(__file__).resolve().parents[2]}:{os.getenv('SMART_LAMP_PORT', '8100')}"
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]
    return f"smartlamp-web-{digest}"


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = "Smart Lamp Web"
    app_version: str = "0.2.0"
    api_version: str = "1"
    instance_id: str = os.getenv("SMART_LAMP_INSTANCE_ID", _default_instance_id())
    host: str = os.getenv("SMART_LAMP_HOST", "0.0.0.0")
    port: int = int(os.getenv("SMART_LAMP_PORT", "8100"))
    udp_port: int = int(os.getenv("SMART_LAMP_UDP_PORT", "41328"))
    tcp_port: int = int(os.getenv("SMART_LAMP_TCP_PORT", "41330"))
    discovery_timeout: float = float(os.getenv("SMART_LAMP_DISCOVERY_TIMEOUT", "3.0"))
    tcp_timeout: float = float(os.getenv("SMART_LAMP_TCP_TIMEOUT", "5.0"))
    stale_gateway_seconds: float = float(os.getenv("SMART_LAMP_STALE_GATEWAY_SECONDS", "30.0"))
    rate_limit_seconds: float = 0.2
    confirm_delay_seconds: float = float(os.getenv("SMART_LAMP_CONFIRM_DELAY", "1.0"))
    refresh_after_write: bool = _env_bool("SMART_LAMP_REFRESH_AFTER_WRITE", True)
    api_token: str | None = os.getenv("SMART_LAMP_API_TOKEN") or None


settings = Settings()
