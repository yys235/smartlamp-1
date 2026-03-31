from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any

from aiohttp import ClientError, ClientResponse, ClientSession, ClientTimeout


LOGGER = logging.getLogger(__name__)


class SmartLampApiError(Exception):
    """Base API error."""


class SmartLampApiAuthError(SmartLampApiError):
    """Authentication failed."""


class SmartLampApiConnectionError(SmartLampApiError):
    """Connection failed."""


@dataclass(slots=True)
class SystemInfo:
    instance_id: str
    version: str
    api_version: str
    auth_enabled: bool


@dataclass(slots=True)
class LampSnapshot:
    device_id: int
    red: int
    green: int
    blue: int
    intensity: int
    is_on: bool
    color_hex: str


@dataclass(slots=True)
class GatewaySnapshot:
    gateway_id: int
    gateway_host: str | None
    connected: bool
    last_seen: datetime | None
    last_communication: datetime | None
    lamp_count: int
    all_off: bool
    lamps: dict[int, LampSnapshot]


@dataclass(slots=True)
class SmartLampSnapshot:
    connected: bool
    gateway_count: int
    selected_gateway_id: int | None
    gateways: dict[int, GatewaySnapshot]


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def _parse_lamp(payload: dict[str, Any]) -> LampSnapshot:
    return LampSnapshot(
        device_id=int(payload["device_id"]),
        red=int(payload["red"]),
        green=int(payload["green"]),
        blue=int(payload["blue"]),
        intensity=int(payload["intensity"]),
        is_on=bool(payload.get("is_on", payload["intensity"] > 0)),
        color_hex=str(payload.get("color_hex", "#ffffff")),
    )


def _parse_gateway(payload: dict[str, Any]) -> GatewaySnapshot:
    lamps = {
        int(lamp_payload["device_id"]): _parse_lamp(lamp_payload)
        for lamp_payload in payload.get("lamps", [])
    }
    return GatewaySnapshot(
        gateway_id=int(payload["gateway_id"]),
        gateway_host=payload.get("gateway_host"),
        connected=bool(payload.get("connected", False)),
        last_seen=_parse_datetime(payload.get("last_seen")),
        last_communication=_parse_datetime(payload.get("last_communication")),
        lamp_count=int(payload.get("lamp_count", len(lamps))),
        all_off=bool(payload.get("all_off", True)),
        lamps=lamps,
    )


def _parse_dashboard(payload: dict[str, Any]) -> SmartLampSnapshot:
    gateways = {
        int(gateway_payload["gateway_id"]): _parse_gateway(gateway_payload)
        for gateway_payload in payload.get("gateways", [])
    }
    current_gateway_payload = payload.get("current_gateway")
    if current_gateway_payload is not None:
        current_gateway = _parse_gateway(current_gateway_payload)
        gateways[current_gateway.gateway_id] = current_gateway

    return SmartLampSnapshot(
        connected=bool(payload.get("connected", False)),
        gateway_count=int(payload.get("gateway_count", len(gateways))),
        selected_gateway_id=payload.get("selected_gateway_id"),
        gateways=gateways,
    )


class SmartLampApiClient:
    def __init__(
        self,
        session: ClientSession,
        base_url: str,
        api_token: str | None,
        request_timeout: float,
    ) -> None:
        self._session = session
        self.base_url = base_url.rstrip("/")
        self._api_token = api_token
        self._request_timeout = request_timeout

    @property
    def auth_headers(self) -> dict[str, str]:
        if not self._api_token:
            return {}
        return {"Authorization": f"Bearer {self._api_token}"}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        timeout = ClientTimeout(total=self._request_timeout)
        try:
            async with self._session.request(
                method,
                url,
                headers=self.auth_headers,
                json=json_body,
                timeout=timeout,
            ) as response:
                return await self._handle_response(response)
        except SmartLampApiError:
            raise
        except ClientError as exc:
            raise SmartLampApiConnectionError(str(exc)) from exc
        except TimeoutError as exc:
            raise SmartLampApiConnectionError("Request timed out") from exc

    async def _handle_response(self, response: ClientResponse) -> dict[str, Any]:
        payload = await response.json()
        if response.status == 401:
            raise SmartLampApiAuthError(payload.get("detail", "Unauthorized"))
        if response.status >= 400:
            raise SmartLampApiError(payload.get("detail", response.reason))
        if payload.get("ok") is not True:
            raise SmartLampApiError(payload.get("message", "Unexpected API response"))
        return payload["status"]

    async def async_get_system_info(self) -> SystemInfo:
        payload = await self._request("GET", "/api/system")
        return SystemInfo(
            instance_id=str(payload["instance_id"]),
            version=str(payload["version"]),
            api_version=str(payload["api_version"]),
            auth_enabled=bool(payload["auth_enabled"]),
        )

    async def async_get_status(self) -> SmartLampSnapshot:
        payload = await self._request("GET", "/api/status")
        return _parse_dashboard(payload)

    async def async_get_gateway(self, gateway_id: int, *, refresh: bool = False) -> GatewaySnapshot:
        suffix = "?refresh=true" if refresh else ""
        payload = await self._request("GET", f"/api/gateways/{gateway_id}{suffix}")
        return _parse_gateway(payload)

    async def async_turn_on_device(
        self,
        gateway_id: int,
        device_id: int,
        *,
        brightness: int,
        rgb_color: tuple[int, int, int],
    ) -> SmartLampSnapshot:
        payload = await self._request(
            "POST",
            f"/api/gateways/{gateway_id}/lamps/{device_id}/on",
            json_body={
                "intensity": brightness,
                "red": rgb_color[0],
                "green": rgb_color[1],
                "blue": rgb_color[2],
            },
        )
        return _parse_dashboard(payload)

    async def async_turn_off_device(self, gateway_id: int, device_id: int) -> SmartLampSnapshot:
        payload = await self._request(
            "POST",
            f"/api/gateways/{gateway_id}/lamps/{device_id}/off",
        )
        return _parse_dashboard(payload)

    async def async_refresh_gateway(self, gateway_id: int) -> SmartLampSnapshot:
        payload = await self._request("POST", f"/api/gateways/{gateway_id}/lamps/refresh")
        return _parse_dashboard(payload)
