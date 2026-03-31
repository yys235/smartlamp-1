from __future__ import annotations

from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_RGB_COLOR, ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
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
    known_lamps: set[tuple[int, int]] = set()

    @callback
    def async_sync_entities() -> None:
        new_entities: list[SmartLampLightEntity] = []
        for gateway in coordinator.data.gateways.values():
            for lamp in gateway.lamps.values():
                lamp_key = (gateway.gateway_id, lamp.device_id)
                if lamp_key in known_lamps:
                    continue
                known_lamps.add(lamp_key)
                new_entities.append(
                    SmartLampLightEntity(
                        coordinator=coordinator,
                        gateway_id=gateway.gateway_id,
                        device_id=lamp.device_id,
                    )
                )
        if new_entities:
            async_add_entities(new_entities)

    async_sync_entities()
    entry.async_on_unload(coordinator.async_add_listener(async_sync_entities))


class SmartLampLightEntity(SmartLampCoordinatorEntity, LightEntity):
    _attr_has_entity_name = True
    _attr_supported_color_modes = {ColorMode.RGB}

    def __init__(
        self,
        coordinator,
        gateway_id: int,
        device_id: int,
    ) -> None:
        super().__init__(coordinator, gateway_id)
        self.device_id = device_id
        self._attr_unique_id = f"{coordinator.instance_id}_{gateway_id}_{device_id}"
        self._attr_name = f"Lamp {device_id}"

    @property
    def lamp(self):
        gateway = self.gateway
        if gateway is None:
            return None
        return gateway.lamps.get(self.device_id)

    @property
    def available(self) -> bool:
        return super().available and self.lamp is not None

    @property
    def is_on(self) -> bool:
        lamp = self.lamp
        return lamp.is_on if lamp is not None else False

    @property
    def brightness(self) -> int | None:
        lamp = self.lamp
        if lamp is None:
            return None
        return lamp.intensity

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        lamp = self.lamp
        if lamp is None:
            return None
        return (lamp.red, lamp.green, lamp.blue)

    @property
    def color_mode(self) -> ColorMode:
        return ColorMode.RGB

    async def async_turn_on(self, **kwargs) -> None:
        lamp = self.lamp
        if lamp is None:
            raise HomeAssistantError("Lamp is unavailable")

        rgb_color = kwargs.get(ATTR_RGB_COLOR, (lamp.red, lamp.green, lamp.blue))
        brightness = kwargs.get(ATTR_BRIGHTNESS, lamp.intensity or 255)
        await self.coordinator.api.async_turn_on_device(
            self.gateway_id,
            self.device_id,
            brightness=brightness,
            rgb_color=rgb_color,
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        if self.lamp is None:
            raise HomeAssistantError("Lamp is unavailable")

        await self.coordinator.api.async_turn_off_device(self.gateway_id, self.device_id)
        await self.coordinator.async_request_refresh()
