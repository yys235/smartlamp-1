from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from app.api.schemas import TurnOffRequest, TurnOnRequest
from app.core.gateway import GatewayUnavailableError, LampNotFoundError, SmartLampGateway


router = APIRouter(prefix="/api", tags=["smart-lamp"])


def get_gateway(request: Request) -> SmartLampGateway:
    return request.app.state.gateway


def api_response(message: str, payload: dict[str, object]) -> dict[str, object]:
    return {"ok": True, "message": message, "status": payload}


@router.get("/status")
def get_status(request: Request, refresh: bool = False) -> dict[str, object]:
    gateway = get_gateway(request)
    return api_response("Fetched lamp status", gateway.get_status(refresh=refresh))


@router.post("/lamps/refresh")
def refresh_lamps(request: Request) -> dict[str, object]:
    gateway = get_gateway(request)
    try:
        gateway.refresh_lamps()
    except GatewayUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return api_response("Refreshed lamp status", gateway.get_status())


@router.post("/lamps/on")
def turn_on(request: Request, body: TurnOnRequest) -> dict[str, object]:
    gateway = get_gateway(request)
    try:
        gateway.turn_on(
            device_id=body.device_id,
            red=body.red,
            green=body.green,
            blue=body.blue,
            intensity=body.intensity,
        )
    except GatewayUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except LampNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return api_response("Updated lamp state", gateway.get_status())


@router.post("/lamps/off")
def turn_off(request: Request, body: TurnOffRequest) -> dict[str, object]:
    gateway = get_gateway(request)
    try:
        gateway.turn_off(device_id=body.device_id)
    except GatewayUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except LampNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return api_response("Turned lamp off", gateway.get_status())
