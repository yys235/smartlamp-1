from __future__ import annotations

from dataclasses import asdict

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_API_TOKEN, DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, object]:
    runtime = hass.data[DOMAIN][entry.entry_id]
    return {
        "entry": async_redact_data({**entry.data, "options": dict(entry.options)}, {CONF_API_TOKEN}),
        "system_info": asdict(runtime["system_info"]),
        "snapshot": asdict(runtime["coordinator"].data),
    }
