import pytest
import uuid
from fastapi.testclient import TestClient
from app.models.core_models import Mesa, PedidoGlobal

GATEWAY_HEADER = {"X-Gateway-Token": "super_secret_test_key"}

@pytest.fixture
def test_mesa(db_session):
    mesa = Mesa(numero=1, capacidad=4, activo=True, qr_token="token_qr_1")
    db_session.add(mesa)
    db_session.commit()
    db_session.refresh(mesa)
    return mesa

def test_get_mesas_admin(client: TestClient, test_mesa, admin_token_header):
    response = client.get("/api/v1/mesas/admin", headers=admin_token_header)
    assert response.status_code == 200
    assert len(response.json()) > 0

def test_crear_mesa(client: TestClient, admin_token_header):
    payload = {"numero": 2, "capacidad": 6, "activo": True}
    response = client.post("/api/v1/mesas/admin", json=payload, headers=admin_token_header)
    assert response.status_code == 201

def test_crear_mesa_duplicada(client: TestClient, test_mesa, admin_token_header):
    payload = {"numero": 1, "capacidad": 6, "activo": True}
    response = client.post("/api/v1/mesas/admin", json=payload, headers=admin_token_header)
    assert response.status_code in [400, 409, 422]

def test_actualizar_mesa(client: TestClient, test_mesa, admin_token_header):
    payload = {"capacidad": 8}
    response = client.put(f"/api/v1/mesas/admin/{test_mesa.id}", json=payload, headers=admin_token_header)
    assert response.status_code == 200
    assert response.json()["capacidad"] == 8

def test_eliminar_mesa(client: TestClient, db_session, admin_token_header):
    mesa = Mesa(numero=3, capacidad=4, activo=True)
    db_session.add(mesa)
    db_session.commit()
    db_session.refresh(mesa)

    response = client.delete(f"/api/v1/mesas/admin/{mesa.id}", headers=admin_token_header)
    assert response.status_code == 200

def test_vincular_mesa_qr_valido(client: TestClient, test_mesa):
    payload = {"codigo_qr_mesa": "token_qr_1"}
    response = client.post("/api/v1/mesas/vincular", json=payload, headers=GATEWAY_HEADER)
    assert response.status_code == 200

def test_vincular_mesa_qr_invalido(client: TestClient):
    payload = {"codigo_qr_mesa": "token_falso"}
    response = client.post("/api/v1/mesas/vincular", json=payload, headers=GATEWAY_HEADER)
    assert response.status_code == 404

def test_vincular_mesa_devuelve_pedido_activo(client: TestClient, db_session, test_mesa):
    pedido_uuid = uuid.uuid4()
    pedido = PedidoGlobal(
        canal_origen="MOVIL",
        mesa=str(test_mesa.numero),
        estado="PENDIENTE",
        factura_local_uuid=pedido_uuid,
    )
    db_session.add(pedido)
    db_session.commit()

    payload = {"codigo_qr_mesa": test_mesa.qr_token}
    response = client.post("/api/v1/mesas/vincular", json=payload, headers=GATEWAY_HEADER)

    assert response.status_code == 200
    assert response.json()["estado_mesa"] == "ABIERTA"
    assert response.json()["factura_local_uuid_activa"] == str(pedido_uuid)

def test_llamar_mesero(client: TestClient, test_mesa):
    payload = {"qr_token": test_mesa.qr_token, "motivo_llamada": "Asistencia"}
    response = client.post(f"/api/v1/mesas/llamar-mesero", json=payload, headers=GATEWAY_HEADER)
    assert response.status_code == 200
