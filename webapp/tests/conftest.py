from __future__ import annotations

from collections.abc import Generator
from dataclasses import replace
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.core.gateway import GatewayUnavailableError, LampNotFoundError
from app.main import app


class FakeGateway:
    def __init__(self, *_args, **_kwargs) -> None:
        self.started = False
        self.turn_on_calls: list[dict[str, object]] = []
        self.turn_off_calls: list[dict[str, object]] = []
        self.refresh_calls: list[int] = []
        self.dashboard = {
            "connected": True,
            "gateway_count": 2,
            "selected_gateway_id": 1001,
            "gateways": [
                {
                    "gateway_id": 1001,
                    "gateway_host": "192.168.1.10",
                    "connected": True,
                    "last_seen": "2026-03-31T10:00:00+00:00",
                    "last_communication": "2026-03-31T10:00:01+00:00",
                    "lamp_count": 2,
                    "all_off": False,
                },
                {
                    "gateway_id": 1002,
                    "gateway_host": "192.168.1.11",
                    "connected": True,
                    "last_seen": "2026-03-31T10:00:02+00:00",
                    "last_communication": None,
                    "lamp_count": 1,
                    "all_off": True,
                },
            ],
            "current_gateway": {
                "gateway_id": 1001,
                "gateway_host": "192.168.1.10",
                "connected": True,
                "last_seen": "2026-03-31T10:00:00+00:00",
                "last_communication": "2026-03-31T10:00:01+00:00",
                "lamp_count": 2,
                "all_off": False,
                "lamps": [
                    {
                        "device_id": 1,
                        "red": 255,
                        "green": 200,
                        "blue": 100,
                        "intensity": 180,
                        "is_on": True,
                        "color_hex": "#ffc864",
                    },
                    {
                        "device_id": 2,
                        "red": 255,
                        "green": 255,
                        "blue": 255,
                        "intensity": 0,
                        "is_on": False,
                        "color_hex": "#ffffff",
                    },
                ],
            },
        }

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.started = False

    def get_system_info(self) -> dict[str, object]:
        return {
            "instance_id": "smartlamp-web-test",
            "version": "0.2.0",
            "api_version": "1",
            "auth_enabled": False,
        }

    def get_dashboard_data(self, gateway_id: int | None = None, refresh: bool = False) -> dict[str, object]:
        dashboard = dict(self.dashboard)
        if gateway_id is not None:
            dashboard["selected_gateway_id"] = gateway_id
            dashboard["current_gateway"] = next(
                (
                    gateway
                    for gateway in [*dashboard["gateways"]]
                    if gateway["gateway_id"] == gateway_id
                ),
                dashboard["current_gateway"],
            )
        if refresh:
            dashboard["refreshed"] = True
        return dashboard

    def list_gateways(self) -> list[dict[str, object]]:
        return list(self.dashboard["gateways"])

    def get_gateway_status(
        self,
        gateway_id: int | None = None,
        *,
        refresh: bool = False,
    ) -> dict[str, object] | None:
        if gateway_id == 4040:
            return None
        current_gateway = self.dashboard["current_gateway"]
        if gateway_id is None:
            return dict(current_gateway)
        matched = next(
            (
                gateway
                for gateway in [current_gateway, *self.dashboard["gateways"]]
                if gateway["gateway_id"] == gateway_id
            ),
            None,
        )
        if matched is None:
            return None
        payload = dict(matched)
        if "lamps" not in payload:
            payload["lamps"] = []
        if refresh:
            payload["refreshed"] = True
        return payload

    def refresh_lamps(self, gateway_id: int | None = None) -> list[object]:
        if gateway_id == 4040:
            raise GatewayUnavailableError("Gateway 4040 not discovered yet")
        self.refresh_calls.append(gateway_id if gateway_id is not None else -1)
        return []

    def turn_on(
        self,
        gateway_id: int | None = None,
        device_id: int | None = None,
        *,
        red: int = 255,
        green: int = 255,
        blue: int = 255,
        intensity: int = 255,
    ) -> list[object]:
        if device_id == 9999:
            raise LampNotFoundError("Lamp 9999 was not found")
        self.turn_on_calls.append(
            {
                "gateway_id": gateway_id,
                "device_id": device_id,
                "red": red,
                "green": green,
                "blue": blue,
                "intensity": intensity,
            }
        )
        return []

    def turn_off(self, gateway_id: int | None = None, device_id: int | None = None) -> list[object]:
        if device_id == 9999:
            raise LampNotFoundError("Lamp 9999 was not found")
        self.turn_off_calls.append(
            {
                "gateway_id": gateway_id,
                "device_id": device_id,
            }
        )
        return []


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient]:
    monkeypatch.setattr("app.main.settings", replace(settings, api_token=None))
    monkeypatch.setattr("app.main.SmartLampGateway", FakeGateway)
    with TestClient(app) as test_client:
        yield test_client
