from __future__ import annotations


def test_home_page_renders_multi_gateway_sections(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "网关列表" in response.text
    assert "当前网关" in response.text
    assert "自动刷新" in response.text


def test_status_endpoint_returns_dashboard_payload(client):
    response = client.get("/api/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["status"]["gateway_count"] == 2
    assert payload["status"]["selected_gateway_id"] == 1001
    assert payload["status"]["current_gateway"]["gateway_id"] == 1001


def test_gateways_endpoint_returns_gateway_list(client):
    response = client.get("/api/gateways")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"]["gateway_count"] == 2
    assert payload["status"]["gateways"][1]["gateway_id"] == 1002


def test_turn_on_route_uses_gateway_scoped_endpoint(client):
    response = client.post(
        "/api/gateways/1001/lamps/on",
        json={
            "device_id": 1,
            "intensity": 120,
            "red": 10,
            "green": 20,
            "blue": 30,
        },
    )

    assert response.status_code == 200
    recorded_call = client.app.state.gateway.turn_on_calls[-1]
    assert recorded_call == {
        "gateway_id": 1001,
        "device_id": 1,
        "red": 10,
        "green": 20,
        "blue": 30,
        "intensity": 120,
    }


def test_compat_turn_on_requires_gateway_id(client):
    response = client.post(
        "/api/lamps/on",
        json={
            "device_id": 1,
            "intensity": 120,
            "red": 10,
            "green": 20,
            "blue": 30,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "gateway_id is required"


def test_turn_off_route_returns_not_found_for_unknown_lamp(client):
    response = client.post("/api/gateways/1001/lamps/off", json={"device_id": 9999})

    assert response.status_code == 404
    assert response.json()["detail"] == "Lamp 9999 was not found"


def test_refresh_route_returns_service_unavailable_for_missing_gateway(client):
    response = client.post("/api/gateways/4040/lamps/refresh")

    assert response.status_code == 503
    assert response.json()["detail"] == "Gateway 4040 not discovered yet"
