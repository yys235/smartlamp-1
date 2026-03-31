from __future__ import annotations

from dataclasses import dataclass
import os


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = "Smart Lamp Web"
    host: str = os.getenv("SMART_LAMP_HOST", "0.0.0.0")
    port: int = int(os.getenv("SMART_LAMP_PORT", "8000"))
    udp_port: int = int(os.getenv("SMART_LAMP_UDP_PORT", "41328"))
    tcp_port: int = int(os.getenv("SMART_LAMP_TCP_PORT", "41330"))
    discovery_timeout: float = float(os.getenv("SMART_LAMP_DISCOVERY_TIMEOUT", "3.0"))
    tcp_timeout: float = float(os.getenv("SMART_LAMP_TCP_TIMEOUT", "5.0"))
    rate_limit_seconds: float = 0.2
    confirm_delay_seconds: float = float(os.getenv("SMART_LAMP_CONFIRM_DELAY", "1.0"))
    refresh_after_write: bool = _env_bool("SMART_LAMP_REFRESH_AFTER_WRITE", True)


settings = Settings()
