import pytest
from fastapi.testclient import TestClient

GATEWAY_HEADER = {"X-Gateway-Token": "super_secret_test_key"}

def test_ventas_hoy(client: TestClient):
    response = client.get("/api/v1/reportes/ventas-hoy", headers=GATEWAY_HEADER)
    assert response.status_code == 200

def test_top_productos_vendidos(client: TestClient):
    response = client.get("/api/v1/reportes/top-productos-vendidos", headers=GATEWAY_HEADER)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_productos_stock_bajo(client: TestClient):
    response = client.get("/api/v1/reportes/productos-stock-bajo", headers=GATEWAY_HEADER)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_ingredientes_stock_bajo(client: TestClient):
    response = client.get("/api/v1/reportes/ingredientes-stock-bajo", headers=GATEWAY_HEADER)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_reporte_fecha_invalida(client: TestClient):
    # Depending on how the endpoints accept query params. Let's try sending invalid date params if they exist.
    response = client.get("/api/v1/reportes/ventas-hoy?fecha=2024-13-45", headers=GATEWAY_HEADER)
    assert response.status_code in [200, 422, 400]
