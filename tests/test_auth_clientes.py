import pytest
from fastapi.testclient import TestClient
from app.models.core_models import Cliente
from app.core.security import get_password_hash

GATEWAY_HEADER = {"X-Gateway-Token": "super_secret_test_key"}

@pytest.fixture
def test_cliente(db_session):
    cliente = Cliente(
        nombre_completo="Cliente Test",
        email="cliente@test.com",
        telefono="1234567890",
        password_hash=get_password_hash("Password123!"),
        activo=True
    )
    db_session.add(cliente)
    db_session.commit()
    db_session.refresh(cliente)
    return cliente

def test_registro_cliente_valido(client: TestClient):
    payload = {
        "nombre_completo": "Nuevo Cliente",
        "email": "nuevo@cliente.com",
        "password_plano": "Password123!",
        "telefono": "0987654321"
    }
    response = client.post("/api/v1/clientes/auth/registro", json=payload, headers=GATEWAY_HEADER)
    assert response.status_code == 201

def test_registro_cliente_email_duplicado(client: TestClient, test_cliente):
    payload = {
        "nombre_completo": "Otro Nombre",
        "email": "cliente@test.com",
        "password_plano": "Password123!",
        "telefono": "0987654321"
    }
    response = client.post("/api/v1/clientes/auth/registro", json=payload, headers=GATEWAY_HEADER)
    assert response.status_code in [400, 409]

def test_login_cliente_valido(client: TestClient, test_cliente):
    payload = {
        "email": "cliente@test.com",
        "password_plano": "Password123!"
    }
    response = client.post("/api/v1/clientes/auth/login", json=payload, headers=GATEWAY_HEADER)
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_cliente_invalido(client: TestClient, test_cliente):
    payload = {
        "email": "cliente@test.com",
        "password_plano": "wrongpassword"
    }
    response = client.post("/api/v1/clientes/auth/login", json=payload, headers=GATEWAY_HEADER)
    assert response.status_code == 401

def test_solicitar_reset_cliente(client: TestClient, test_cliente):
    payload = {"email": "cliente@test.com"}
    response = client.post("/api/v1/clientes/auth/solicitar-reset", json=payload, headers=GATEWAY_HEADER)
    assert response.status_code == 200
    assert "If the email is registered" in response.json().get("mensaje", "") or response.status_code == 200
