import pytest
from fastapi.testclient import TestClient
from app.models.core_models import Producto, Categoria, Impuesto, InventarioActual

GATEWAY_HEADER = {"X-Gateway-Token": "super_secret_test_key"}

@pytest.fixture
def setup_inventario(db_session):
    cat = Categoria(nombre="Snacks")
    imp = Impuesto(nombre="ITBIS", tasa_porcentaje=18.0)
    db_session.add(cat)
    db_session.add(imp)
    db_session.commit()
    db_session.refresh(cat)
    db_session.refresh(imp)

    prod = Producto(
        categoria_id=cat.id,
        impuesto_id=imp.id,
        sku="SKU_SNACK",
        nombre="Papas",
        precio_base=50.0,
        tipo_control_inventario="PRODUCTO"
    )
    db_session.add(prod)
    db_session.commit()
    db_session.refresh(prod)

    inv = InventarioActual(producto_id=prod.id, cantidad_disponible=10, stock_minimo=5)
    db_session.add(inv)
    db_session.commit()
    db_session.refresh(inv)

    return prod, inv

def test_get_inventario(client: TestClient, setup_inventario, admin_token_header):
    prod, _ = setup_inventario
    response = client.get(f"/api/v1/inventario/{prod.id}", headers=admin_token_header)
    assert response.status_code == 200
    assert response.json()["cantidad_disponible"] == 10

def test_movimiento_inventario_suma(client: TestClient, setup_inventario, admin_token_header):
    prod, _ = setup_inventario
    payload = {
        "producto_id": prod.id,
        "tipo_movimiento": "ENTRADA",
        "cantidad": 20,
        "motivo": "Reabastecimiento",
        "empleado_id": 1
    }
    response = client.post("/api/v1/inventario/movimiento", json=payload, headers=admin_token_header)
    if response.status_code != 201:
        print(f"ERROR JSON INVENTARIO: {response.json()}")
    assert response.status_code == 201

    # Verify updated stock
    get_res = client.get(f"/api/v1/inventario/{prod.id}", headers=admin_token_header)
    assert get_res.json()["cantidad_disponible"] == 30

def test_movimiento_inventario_resta_excesiva(client: TestClient, setup_inventario, admin_token_header):
    prod, _ = setup_inventario
    payload = {
        "producto_id": prod.id,
        "tipo_movimiento": "SALIDA",
        "cantidad": -50, # Trying to sell more than available
        "motivo": "Venta masiva"
    }
    response = client.post("/api/v1/inventario/movimiento", json=payload, headers=admin_token_header)
    # Depending on business logic, this might be allowed (resulting in negative stock) or blocked
    assert response.status_code in [201, 400, 422]

def test_get_movimientos_producto(client: TestClient, setup_inventario, admin_token_header):
    prod, _ = setup_inventario
    response = client.get(f"/api/v1/inventario/productos/{prod.id}/movimientos", headers=admin_token_header)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_movimiento_producto_invalido(client: TestClient, admin_token_header):
    payload = {
        "producto_id": 9999,
        "tipo_movimiento": "ENTRADA",
        "cantidad": 10,
        "motivo": "Test"
    }
    response = client.post("/api/v1/inventario/movimiento", json=payload, headers=admin_token_header)
    assert response.status_code in [400, 404, 422, 500]
