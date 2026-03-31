from __future__ import annotations

from pydantic import BaseModel, Field


class TurnOnRequest(BaseModel):
    gateway_id: int | None = Field(default=None)
    device_id: int | None = Field(default=None)
    intensity: int = Field(default=255, ge=0, le=255)
    red: int = Field(default=255, ge=0, le=255)
    green: int = Field(default=255, ge=0, le=255)
    blue: int = Field(default=255, ge=0, le=255)


class TurnOffRequest(BaseModel):
    gateway_id: int | None = Field(default=None)
    device_id: int | None = Field(default=None)
