from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SmartLampApiAuthError, SmartLampApiClient, SmartLampApiError, SmartLampSnapshot
from .const import DOMAIN


LOGGER = logging.getLogger(__name__)


class SmartLampDataUpdateCoordinator(DataUpdateCoordinator[SmartLampSnapshot]):
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: SmartLampApiClient,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api
        self.instance_id = ""

    async def _async_update_data(self) -> SmartLampSnapshot:
        try:
            return await self.api.async_get_status()
        except SmartLampApiAuthError as exc:
            raise ConfigEntryAuthFailed(str(exc)) from exc
        except SmartLampApiError as exc:
            raise UpdateFailed(str(exc)) from exc
