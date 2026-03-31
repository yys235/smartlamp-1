from __future__ import annotations

from collections.abc import Callable
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
    """Raised when the lamp gateway has not been discovered yet."""


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


class SmartLampGateway:
    def __init__(self, app_settings: Settings = settings) -> None:
        self.settings = app_settings
        self._state_lock = threading.RLock()
        self._request_lock = threading.Lock()
        self._discovery_event = threading.Event()
        self._stop_event = threading.Event()
        self._listener_thread: threading.Thread | None = None
        self._udp_socket: socket.socket | None = None
        self._gateway_host: str | None = None
        self._gateway_id: int | None = None
        self._connected = False
        self._removed_devices = 0
        self._added_devices = 0
        self._last_seen: datetime | None = None
        self._last_communication: datetime | None = None
        self._last_request_monotonic = 0.0
        self._lamps: list[Lamp] = []

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

            with self._state_lock:
                changed = self._connected and (
                    removed != self._removed_devices or added != self._added_devices
                )
                self._gateway_host = address[0]
                self._gateway_id = gateway_id
                self._connected = True
                self._removed_devices = removed
                self._added_devices = added
                self._last_seen = utc_now()

            self._discovery_event.set()

            if changed:
                try:
                    self.refresh_lamps()
                except Exception:
                    LOGGER.exception("Failed to refresh lamps after gateway change")

    def _require_gateway(self) -> tuple[str, int]:
        if not self._discovery_event.wait(timeout=self.settings.discovery_timeout):
            raise GatewayUnavailableError("Gateway not discovered yet")

        with self._state_lock:
            if not self._gateway_host or self._gateway_id is None:
                raise GatewayUnavailableError("Gateway state is incomplete")
            return self._gateway_host, self._gateway_id

    def _rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_monotonic
        remaining = self.settings.rate_limit_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def _send_request(self, payload: bytes) -> bytes:
        gateway_host, _ = self._require_gateway()

        with self._request_lock:
            self._rate_limit()
            with socket.create_connection(
                (gateway_host, self.settings.tcp_port),
                timeout=self.settings.tcp_timeout,
            ) as tcp_socket:
                tcp_socket.settimeout(self.settings.tcp_timeout)
                tcp_socket.sendall(payload)
                header = read_exact(tcp_socket, 10)
                body = b""
                if len(header) == 10 and header[9] > 0:
                    body = read_exact(tcp_socket, header[9])

            with self._state_lock:
                self._last_request_monotonic = time.monotonic()
                self._last_communication = utc_now()

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

    def refresh_lamps(self) -> list[Lamp]:
        _, gateway_id = self._require_gateway()
        data = self._send_request(self._build_get_lamps_request(gateway_id))
        if not data:
            with self._state_lock:
                self._lamps = []
            return []

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
            self._lamps = lamps

        return [lamp.copy() for lamp in lamps]

    def _mutate_lamps(
        self,
        device_id: int | None,
        mutator: Callable[[Lamp], None],
    ) -> list[Lamp]:
        lamps = self.refresh_lamps()
        if not lamps:
            raise GatewayUnavailableError("No lamps returned from gateway")

        matched = False
        for lamp in lamps:
            if device_id is None or lamp.device_id == device_id:
                mutator(lamp)
                matched = True

        if not matched:
            raise LampNotFoundError(f"Lamp {device_id} was not found")

        self._send_request(self._build_update_lamps_request(lamps))

        if not self.settings.refresh_after_write:
            with self._state_lock:
                self._lamps = [lamp.copy() for lamp in lamps]
            return lamps

        time.sleep(self.settings.confirm_delay_seconds)
        refreshed = self.refresh_lamps()
        if refreshed != lamps:
            self._send_request(self._build_update_lamps_request(lamps))
            time.sleep(self.settings.confirm_delay_seconds)
            refreshed = self.refresh_lamps()
        return refreshed

    def turn_on(
        self,
        device_id: int | None = None,
        *,
        red: int = 255,
        green: int = 255,
        blue: int = 255,
        intensity: int = 255,
    ) -> list[Lamp]:
        return self._mutate_lamps(
            device_id,
            lambda lamp: lamp.set_rgbi(red=red, green=green, blue=blue, intensity=intensity),
        )

    def turn_off(self, device_id: int | None = None) -> list[Lamp]:
        return self._mutate_lamps(device_id, lambda lamp: lamp.set_off())

    def get_status(self, refresh: bool = False) -> dict[str, object]:
        if refresh and self._connected:
            try:
                self.refresh_lamps()
            except GatewayUnavailableError:
                LOGGER.debug("Gateway unavailable during refresh request")

        with self._state_lock:
            lamps = [lamp.copy() for lamp in self._lamps]
            return {
                "connected": self._connected,
                "gateway_host": self._gateway_host,
                "gateway_id": self._gateway_id,
                "last_seen": self._last_seen.isoformat() if self._last_seen else None,
                "last_communication": (
                    self._last_communication.isoformat()
                    if self._last_communication
                    else None
                ),
                "lamp_count": len(lamps),
                "all_off": all(lamp.intensity == 0 for lamp in lamps) if lamps else True,
                "lamps": [lamp.to_dict() for lamp in lamps],
            }
