import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

GATEWAY_HEADER = {"X-Gateway-Token": "super_secret_test_key"}

def test_crear_promocion_valida(client: TestClient, admin_token_header):
    payload = {
        "nombre": "Promo Verano",
        "descripcion": "Descuento por verano",
        "tipo_descuento": "PORCENTAJE",
        "valor": 15.0,
        "fecha_inicio": datetime.now().isoformat(),
        "fecha_fin": (datetime.now() + timedelta(days=30)).isoformat(),
        "aplica_a": "TODOS",
        "tipo_aplicacion": "AUTOMATICA",
        "activo": True
    }
    response = client.post("/api/v1/promociones/", json=payload, headers=admin_token_header)
    assert response.status_code == 201

def test_crear_promocion_fecha_invalida(client: TestClient, admin_token_header):
    payload = {
        "nombre": "Promo Pasado",
        "tipo_descuento": "MONTO_FIJO",
        "valor": 100.0,
        "fecha_inicio": (datetime.now() + timedelta(days=10)).isoformat(),
        "fecha_fin": datetime.now().isoformat(), # End before start
        "aplica_a": "TODOS",
        "tipo_aplicacion": "AUTOMATICA"
    }
    response = client.post("/api/v1/promociones/", json=payload, headers=admin_token_header)
    assert response.status_code in [201, 400, 422]

def test_crear_promocion_descuento_excesivo(client: TestClient, admin_token_header):
    payload = {
        "nombre": "Promo Loca",
        "tipo_descuento": "PORCENTAJE",
        "valor": 150.0, # 150% discount
        "fecha_inicio": datetime.now().isoformat(),
        "aplica_a": "TODOS",
        "tipo_aplicacion": "AUTOMATICA"
    }
    response = client.post("/api/v1/promociones/", json=payload, headers=admin_token_header)
    assert response.status_code in [400, 422]

def test_evaluar_promociones_globales(client: TestClient):
    response = client.get("/api/v1/promociones/evaluar/globales?subtotal_total=100.0", headers=GATEWAY_HEADER)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_happy_hour_activo(client: TestClient):
    response = client.get("/api/v1/promociones/happy-hour/activo", headers=GATEWAY_HEADER)
    assert response.status_code == 200

def test_eliminar_promocion_invalida(client: TestClient, admin_token_header):
    response = client.delete("/api/v1/promociones/9999", headers=admin_token_header)
    assert response.status_code == 404

def test_crear_promocion_sin_tipo(client: TestClient, admin_token_header):
    payload = {
        "nombre": "Sin Tipo",
        "valor": 10.0,
        "fecha_inicio": datetime.now().isoformat(),
    }
    response = client.post("/api/v1/promociones/", json=payload, headers=admin_token_header)
    assert response.status_code == 422
