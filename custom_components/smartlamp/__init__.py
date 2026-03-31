from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SmartLampApiClient
from .const import (
    CONF_API_TOKEN,
    CONF_BASE_URL,
    CONF_REQUEST_TIMEOUT,
    CONF_SCAN_INTERVAL,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import SmartLampDataUpdateCoordinator


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    api = SmartLampApiClient(
        session=async_get_clientsession(hass),
        base_url=entry.data[CONF_BASE_URL],
        api_token=entry.data.get(CONF_API_TOKEN),
        request_timeout=entry.options.get(CONF_REQUEST_TIMEOUT, entry.data.get(CONF_REQUEST_TIMEOUT, DEFAULT_REQUEST_TIMEOUT)),
    )
    coordinator = SmartLampDataUpdateCoordinator(
        hass=hass,
        entry=entry,
        api=api,
        scan_interval=entry.options.get(CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)),
    )
    system_info = await api.async_get_system_info()
    coordinator.instance_id = system_info.instance_id
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
        "system_info": system_info,
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
