from __future__ import annotations

from dataclasses import asdict, dataclass


def clamp_channel(value: int) -> int:
    return max(0, min(255, int(value)))


@dataclass(slots=True)
class Lamp:
    device_id: int
    red: int
    green: int
    blue: int
    intensity: int

    def copy(self) -> "Lamp":
        return Lamp(
            device_id=self.device_id,
            red=self.red,
            green=self.green,
            blue=self.blue,
            intensity=self.intensity,
        )

    def set_rgbi(self, red: int, green: int, blue: int, intensity: int) -> None:
        self.red = clamp_channel(red)
        self.green = clamp_channel(green)
        self.blue = clamp_channel(blue)
        self.intensity = clamp_channel(intensity)

    def set_off(self) -> None:
        self.intensity = 0

    @property
    def is_on(self) -> bool:
        return self.intensity > 0

    @property
    def color_hex(self) -> str:
        return f"#{self.red:02x}{self.green:02x}{self.blue:02x}"

    def to_protocol_bytes(self) -> bytes:
        return (
            self.device_id.to_bytes(4, byteorder="little", signed=True)
            + bytes(
                (
                    clamp_channel(self.intensity),
                    clamp_channel(self.red),
                    clamp_channel(self.green),
                    clamp_channel(self.blue),
                )
            )
        )

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["is_on"] = self.is_on
        payload["color_hex"] = self.color_hex
        return payload
