from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import SmartLampCoordinatorEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    coordinator = runtime["coordinator"]
    known_gateways: set[int] = set()

    @callback
    def async_sync_entities() -> None:
        new_entities: list[SmartLampRefreshGatewayButton] = []
        for gateway in coordinator.data.gateways.values():
            if gateway.gateway_id in known_gateways:
                continue
            known_gateways.add(gateway.gateway_id)
            new_entities.append(SmartLampRefreshGatewayButton(coordinator, gateway.gateway_id))
        if new_entities:
            async_add_entities(new_entities)

    async_sync_entities()
    entry.async_on_unload(coordinator.async_add_listener(async_sync_entities))


class SmartLampRefreshGatewayButton(SmartLampCoordinatorEntity, ButtonEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, gateway_id: int) -> None:
        super().__init__(coordinator, gateway_id)
        self._attr_unique_id = f"{coordinator.instance_id}_{gateway_id}_refresh"
        self._attr_name = "Refresh"

    async def async_press(self) -> None:
        await self.coordinator.api.async_refresh_gateway(self.gateway_id)
        await self.coordinator.async_request_refresh()
