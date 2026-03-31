from __future__ import annotations

from homeassistant.const import Platform


DOMAIN = "smartlamp"

CONF_BASE_URL = "base_url"
CONF_API_TOKEN = "api_token"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_REQUEST_TIMEOUT = "request_timeout"

DEFAULT_SCAN_INTERVAL = 10
DEFAULT_REQUEST_TIMEOUT = 5.0

PLATFORMS: tuple[Platform, ...] = (Platform.LIGHT, Platform.BUTTON)
