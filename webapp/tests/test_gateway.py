from __future__ import annotations

from datetime import timedelta

from app.core.config import Settings
from app.core.gateway import GatewayState, SmartLampGateway, utc_now


def test_stale_gateway_is_marked_offline():
    gateway = SmartLampGateway(Settings(stale_gateway_seconds=30.0))
    gateway._gateways[1001] = GatewayState(  # noqa: SLF001
        gateway_id=1001,
        host="192.168.1.10",
        last_seen=utc_now() - timedelta(seconds=45),
    )

    payload = gateway.list_gateways()

    assert payload[0]["gateway_id"] == 1001
    assert payload[0]["connected"] is False


def test_dashboard_connected_false_when_all_gateways_are_stale():
    gateway = SmartLampGateway(Settings(stale_gateway_seconds=30.0))
    gateway._gateways[1001] = GatewayState(  # noqa: SLF001
        gateway_id=1001,
        host="192.168.1.10",
        last_seen=utc_now() - timedelta(seconds=31),
    )

    payload = gateway.get_dashboard_data(gateway_id=1001)

    assert payload["connected"] is False
    assert payload["current_gateway"]["connected"] is False
