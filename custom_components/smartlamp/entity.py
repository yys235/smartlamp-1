from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SmartLampDataUpdateCoordinator


class SmartLampCoordinatorEntity(CoordinatorEntity[SmartLampDataUpdateCoordinator]):
    def __init__(self, coordinator: SmartLampDataUpdateCoordinator, gateway_id: int) -> None:
        super().__init__(coordinator)
        self.gateway_id = gateway_id

    @property
    def gateway(self):
        return self.coordinator.data.gateways.get(self.gateway_id)

    @property
    def available(self) -> bool:
        gateway = self.gateway
        return super().available and gateway is not None and gateway.connected

    @property
    def device_info(self) -> DeviceInfo:
        gateway = self.gateway
        gateway_host = gateway.gateway_host if gateway is not None else None
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.coordinator.instance_id}_gateway_{self.gateway_id}")},
            name=f"SmartLamp Gateway {self.gateway_id}",
            manufacturer="SmartLamp",
            model="Gateway",
            configuration_url=self.coordinator.api.base_url,
            suggested_area="Lighting" if gateway_host else None,
        )
