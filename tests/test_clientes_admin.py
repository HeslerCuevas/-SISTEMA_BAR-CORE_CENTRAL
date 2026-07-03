import pytest
from fastapi.testclient import TestClient
from app.models.core_models import Cliente

GATEWAY_HEADER = {"X-Gateway-Token": "super_secret_test_key"}

def test_get_all_clientes_admin(client: TestClient, admin_token_header):
    response = client.get("/api/v1/admin/clientes/", headers=admin_token_header)
    assert response.status_code == 200
    assert isinstance(response.json()["clientes"], list)

def test_get_cliente_admin_invalido(client: TestClient, admin_token_header):
    response = client.get("/api/v1/admin/clientes/99999", headers=admin_token_header)
    assert response.status_code == 404

def test_desactivar_y_reactivar_cliente(client: TestClient, db_session, admin_token_header):
    cliente = Cliente(
        nombre_completo="Deactivate Me",
        email="deac@cliente.com",
        password_hash="hash",
        activo=True
    )
    db_session.add(cliente)
    db_session.commit()
    db_session.refresh(cliente)

    # Desactivar
    response = client.post(f"/api/v1/admin/clientes/{cliente.id}/desactivar", headers=admin_token_header)
    assert response.status_code == 200

    # Verify deactivated
    get_res = client.get(f"/api/v1/admin/clientes/{cliente.id}", headers=admin_token_header)
    assert get_res.json()["activo"] is False

    # Reactivar
    response_re = client.post(f"/api/v1/admin/clientes/{cliente.id}/reactivar", headers=admin_token_header)
    assert response_re.status_code == 200

    # Verify reactivated
    get_res2 = client.get(f"/api/v1/admin/clientes/{cliente.id}", headers=admin_token_header)
    assert get_res2.json()["activo"] is True
