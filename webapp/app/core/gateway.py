from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import socket
import threading
import time
from typing import Final

from .config import Settings, settings
from .models import Lamp


LOGGER: Final = logging.getLogger(__name__)


class GatewayUnavailableError(RuntimeError):
    """Raised when the requested lamp gateway is not available."""


class LampNotFoundError(RuntimeError):
    """Raised when the requested lamp is missing from the gateway response."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def read_exact(sock: socket.socket, size: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        chunk = sock.recv(size - len(chunks))
        if not chunk:
            break
        chunks.extend(chunk)
    return bytes(chunks)


@dataclass(slots=True)
class GatewayState:
    gateway_id: int
    host: str
    connected: bool = True
    removed_devices: int = 0
    added_devices: int = 0
    last_seen: datetime | None = None
    last_communication: datetime | None = None
    last_request_monotonic: float = 0.0
    lamps: list[Lamp] = field(default_factory=list)
    request_lock: threading.Lock = field(
        default_factory=threading.Lock,
        repr=False,
        compare=False,
    )


class SmartLampGateway:
    def __init__(self, app_settings: Settings = settings) -> None:
        self.settings = app_settings
        self._state_lock = threading.RLock()
        self._discovery_event = threading.Event()
        self._stop_event = threading.Event()
        self._listener_thread: threading.Thread | None = None
        self._udp_socket: socket.socket | None = None
        self._gateways: dict[int, GatewayState] = {}

    def get_system_info(self) -> dict[str, object]:
        return {
            "instance_id": self.settings.instance_id,
            "version": self.settings.app_version,
            "api_version": self.settings.api_version,
            "auth_enabled": bool(self.settings.api_token),
        }

    def start(self) -> None:
        if self._listener_thread and self._listener_thread.is_alive():
            return

        self._stop_event.clear()
        self._listener_thread = threading.Thread(
            target=self._udp_listener,
            name="smart-lamp-udp-listener",
            daemon=True,
        )
        self._listener_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._udp_socket is not None:
            try:
                self._udp_socket.close()
            except OSError:
                LOGGER.debug("Failed to close UDP socket cleanly", exc_info=True)
        if self._listener_thread and self._listener_thread.is_alive():
            self._listener_thread.join(timeout=1.0)

    def _udp_listener(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", self.settings.udp_port))
        sock.settimeout(1.0)
        self._udp_socket = sock
        LOGGER.info("Listening for gateway broadcasts on UDP %s", self.settings.udp_port)

        while not self._stop_event.is_set():
            try:
                packet, address = sock.recvfrom(2048)
            except socket.timeout:
                continue
            except OSError:
                if self._stop_event.is_set():
                    break
                LOGGER.exception("UDP listener failed")
                continue

            if len(packet) < 23:
                continue

            gateway_id = int.from_bytes(packet[2:6], byteorder="little", signed=True)
            removed = packet[21]
            added = packet[22]
            changed = False

            with self._state_lock:
                existing = self._gateways.get(gateway_id)
                if existing is None:
                    existing = GatewayState(gateway_id=gateway_id, host=address[0])
                    self._gateways[gateway_id] = existing

                changed = existing.connected and (
                    removed != existing.removed_devices or added != existing.added_devices
                )
                existing.host = address[0]
                existing.connected = True
                existing.removed_devices = removed
                existing.added_devices = added
                existing.last_seen = utc_now()

            self._discovery_event.set()

            if changed:
                try:
                    self.refresh_lamps(gateway_id)
                except Exception:
                    LOGGER.exception("Failed to refresh lamps after gateway change for %s", gateway_id)

    def _wait_for_any_gateway(self) -> None:
        with self._state_lock:
            if self._gateways:
                return
        if not self._discovery_event.wait(timeout=self.settings.discovery_timeout):
            raise GatewayUnavailableError("Gateway not discovered yet")

    def _latest_gateway_id(self) -> int:
        self._wait_for_any_gateway()
        with self._state_lock:
            if not self._gateways:
                raise GatewayUnavailableError("Gateway not discovered yet")

            latest = max(
                self._gateways.values(),
                key=lambda gateway: gateway.last_seen or datetime.min.replace(tzinfo=timezone.utc),
            )
            return latest.gateway_id

    def _resolve_gateway_id(self, gateway_id: int | None) -> int:
        if gateway_id is None:
            return self._latest_gateway_id()

        self._wait_for_any_gateway()
        with self._state_lock:
            if gateway_id not in self._gateways:
                raise GatewayUnavailableError(f"Gateway {gateway_id} not discovered yet")
        return gateway_id

    def _get_gateway(self, gateway_id: int | None) -> GatewayState:
        resolved_gateway_id = self._resolve_gateway_id(gateway_id)
        with self._state_lock:
            gateway = self._gateways.get(resolved_gateway_id)
            if gateway is None:
                raise GatewayUnavailableError(f"Gateway {resolved_gateway_id} not discovered yet")
            return gateway

    def _rate_limit(self, gateway: GatewayState) -> None:
        elapsed = time.monotonic() - gateway.last_request_monotonic
        remaining = self.settings.rate_limit_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def _send_request(self, gateway: GatewayState, payload: bytes) -> bytes:
        with gateway.request_lock:
            self._rate_limit(gateway)
            with socket.create_connection(
                (gateway.host, self.settings.tcp_port),
                timeout=self.settings.tcp_timeout,
            ) as tcp_socket:
                tcp_socket.settimeout(self.settings.tcp_timeout)
                tcp_socket.sendall(payload)
                header = read_exact(tcp_socket, 10)
                body = b""
                if len(header) == 10 and header[9] > 0:
                    body = read_exact(tcp_socket, header[9])

            with self._state_lock:
                gateway.last_request_monotonic = time.monotonic()
                gateway.last_communication = utc_now()

            return body

    def _build_get_lamps_request(self, gateway_id: int) -> bytes:
        return bytes((0xF3, 0xD4)) + gateway_id.to_bytes(
            4, byteorder="big", signed=True
        ) + bytes((0x00, 0x00, 0x1D, 0x05, 0x00, 0x00, 0x00, 0x43, 0x00))

    def _build_update_lamps_request(self, lamps: list[Lamp]) -> bytes:
        lamp_bytes = b"".join(lamp.to_protocol_bytes() for lamp in lamps)
        length = len(lamp_bytes) + 4
        return bytes((0xF2, 0xC2, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x1D, length)) + bytes(
            (0x00, 0x00, 0x00, 0x43)
        ) + lamp_bytes

    def _is_gateway_connected(self, gateway: GatewayState) -> bool:
        if gateway.last_seen is None:
            return False
        return (utc_now() - gateway.last_seen).total_seconds() <= self.settings.stale_gateway_seconds

    def _serialize_gateway_summary(self, gateway: GatewayState) -> dict[str, object]:
        connected = self._is_gateway_connected(gateway)
        return {
            "gateway_id": gateway.gateway_id,
            "gateway_host": gateway.host,
            "connected": connected,
            "last_seen": gateway.last_seen.isoformat() if gateway.last_seen else None,
            "last_communication": (
                gateway.last_communication.isoformat()
                if gateway.last_communication
                else None
            ),
            "lamp_count": len(gateway.lamps),
            "all_off": all(lamp.intensity == 0 for lamp in gateway.lamps) if gateway.lamps else True,
        }

    def _serialize_gateway_status(self, gateway: GatewayState) -> dict[str, object]:
        payload = self._serialize_gateway_summary(gateway)
        payload["lamps"] = [lamp.to_dict() for lamp in gateway.lamps]
        return payload

    def _sorted_gateways(self) -> list[GatewayState]:
        with self._state_lock:
            return sorted(
                self._gateways.values(),
                key=lambda gateway: (
                    gateway.last_seen or datetime.min.replace(tzinfo=timezone.utc),
                    gateway.gateway_id,
                ),
                reverse=True,
            )

    def list_gateways(self) -> list[dict[str, object]]:
        return [self._serialize_gateway_summary(gateway) for gateway in self._sorted_gateways()]

    def refresh_lamps(self, gateway_id: int | None = None) -> list[Lamp]:
        gateway = self._get_gateway(gateway_id)
        data = self._send_request(gateway, self._build_get_lamps_request(gateway.gateway_id))
        lamps: list[Lamp] = []
        if data:
            lamps = [
                Lamp(
                    device_id=int.from_bytes(data[index : index + 4], byteorder="little", signed=True),
                    red=data[index + 6],
                    green=data[index + 5],
                    blue=data[index + 4],
                    intensity=data[index + 7],
                )
                for index in range(0, len(data), 8)
            ]

        with self._state_lock:
            gateway.lamps = lamps

        return [lamp.copy() for lamp in lamps]

    def _mutate_lamps(
        self,
        gateway_id: int | None,
        device_id: int | None,
        mutator: Callable[[Lamp], None],
    ) -> list[Lamp]:
        resolved_gateway_id = self._resolve_gateway_id(gateway_id)
        lamps = self.refresh_lamps(resolved_gateway_id)
        if not lamps:
            raise GatewayUnavailableError(f"No lamps returned from gateway {resolved_gateway_id}")

        matched = False
        for lamp in lamps:
            if device_id is None or lamp.device_id == device_id:
                mutator(lamp)
                matched = True

        if not matched:
            raise LampNotFoundError(f"Lamp {device_id} was not found in gateway {resolved_gateway_id}")

        gateway = self._get_gateway(resolved_gateway_id)
        self._send_request(gateway, self._build_update_lamps_request(lamps))

        if not self.settings.refresh_after_write:
            with self._state_lock:
                gateway.lamps = [lamp.copy() for lamp in lamps]
            return lamps

        time.sleep(self.settings.confirm_delay_seconds)
        refreshed = self.refresh_lamps(resolved_gateway_id)
        if refreshed != lamps:
            self._send_request(gateway, self._build_update_lamps_request(lamps))
            time.sleep(self.settings.confirm_delay_seconds)
            refreshed = self.refresh_lamps(resolved_gateway_id)
        return refreshed

    def turn_on(
        self,
        gateway_id: int | None = None,
        device_id: int | None = None,
        *,
        red: int = 255,
        green: int = 255,
        blue: int = 255,
        intensity: int = 255,
    ) -> list[Lamp]:
        return self._mutate_lamps(
            gateway_id,
            device_id,
            lambda lamp: lamp.set_rgbi(red=red, green=green, blue=blue, intensity=intensity),
        )

    def turn_off(self, gateway_id: int | None = None, device_id: int | None = None) -> list[Lamp]:
        return self._mutate_lamps(gateway_id, device_id, lambda lamp: lamp.set_off())

    def get_gateway_status(
        self,
        gateway_id: int | None = None,
        *,
        refresh: bool = False,
    ) -> dict[str, object] | None:
        try:
            gateway = self._get_gateway(gateway_id)
        except GatewayUnavailableError:
            return None

        if refresh:
            self.refresh_lamps(gateway.gateway_id)
            gateway = self._get_gateway(gateway.gateway_id)

        with self._state_lock:
            return self._serialize_gateway_status(gateway)

    def get_dashboard_data(
        self,
        gateway_id: int | None = None,
        *,
        refresh: bool = False,
    ) -> dict[str, object]:
        selected_gateway_id: int | None = gateway_id
        current_gateway = None

        try:
            resolved_gateway_id = self._resolve_gateway_id(gateway_id)
            selected_gateway_id = resolved_gateway_id
            current_gateway = self.get_gateway_status(resolved_gateway_id, refresh=refresh)
        except GatewayUnavailableError:
            selected_gateway_id = None

        gateways = self.list_gateways()
        return {
            "connected": any(gateway["connected"] for gateway in gateways),
            "gateway_count": len(gateways),
            "selected_gateway_id": selected_gateway_id,
            "gateways": gateways,
            "current_gateway": current_gateway,
        }
