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
def get_status(
    request: Request,
    refresh: bool = False,
    gateway_id: int | None = None,
) -> dict[str, object]:
    gateway = get_gateway(request)
    return api_response(
        "Fetched lamp status",
        gateway.get_dashboard_data(gateway_id=gateway_id, refresh=refresh),
    )


@router.get("/gateways")
def list_gateways(request: Request) -> dict[str, object]:
    gateway = get_gateway(request)
    gateways = gateway.list_gateways()
    return api_response(
        "Fetched gateways",
        {
            "gateways": gateways,
            "gateway_count": len(gateways),
        },
    )


@router.post("/gateways/{gateway_id}/lamps/refresh")
def refresh_gateway_lamps(request: Request, gateway_id: int) -> dict[str, object]:
    gateway = get_gateway(request)
    try:
        gateway.refresh_lamps(gateway_id)
    except GatewayUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return api_response(
        "Refreshed lamp status",
        gateway.get_dashboard_data(gateway_id=gateway_id),
    )


@router.post("/gateways/{gateway_id}/lamps/on")
def turn_on_by_gateway(request: Request, gateway_id: int, body: TurnOnRequest) -> dict[str, object]:
    gateway = get_gateway(request)
    try:
        gateway.turn_on(
            gateway_id=gateway_id,
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
    return api_response(
        "Updated lamp state",
        gateway.get_dashboard_data(gateway_id=gateway_id),
    )


@router.post("/gateways/{gateway_id}/lamps/off")
def turn_off_by_gateway(request: Request, gateway_id: int, body: TurnOffRequest) -> dict[str, object]:
    gateway = get_gateway(request)
    try:
        gateway.turn_off(gateway_id=gateway_id, device_id=body.device_id)
    except GatewayUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except LampNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return api_response(
        "Turned lamp off",
        gateway.get_dashboard_data(gateway_id=gateway_id),
    )


@router.post("/lamps/refresh")
def refresh_lamps(request: Request, body: TurnOffRequest) -> dict[str, object]:
    if body.gateway_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="gateway_id is required")
    return refresh_gateway_lamps(request, body.gateway_id)


@router.post("/lamps/on")
def turn_on(request: Request, body: TurnOnRequest) -> dict[str, object]:
    if body.gateway_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="gateway_id is required")
    return turn_on_by_gateway(request, body.gateway_id, body)


@router.post("/lamps/off")
def turn_off(request: Request, body: TurnOffRequest) -> dict[str, object]:
    if body.gateway_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="gateway_id is required")
    return turn_off_by_gateway(request, body.gateway_id, body)
