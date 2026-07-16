import hashlib
import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from app.models.core_models import Cliente, ClienteOtpCode
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
    assert response.json()["email_verificado"] is False

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
    assert response.json()["email"] == "cliente@test.com"
    assert response.json()["email_verificado"] is False

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
    assert response.status_code in [200, 503]


def test_verificar_email_por_otp(client: TestClient, db_session, test_cliente):
    test_cliente.email_verificado = False
    db_session.add(test_cliente)
    db_session.commit()

    login_response = client.post(
        "/api/v1/clientes/auth/login",
        json={"email": "cliente@test.com", "password_plano": "Password123!"},
        headers=GATEWAY_HEADER,
    )
    token = login_response.json()["access_token"]
    auth_headers = {**GATEWAY_HEADER, "Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/v1/clientes/auth/solicitar-verificacion-email",
        headers=auth_headers,
    )
    assert response.status_code == 200

    otp = db_session.exec(
        select(ClienteOtpCode).where(
            ClienteOtpCode.cliente_id == test_cliente.id,
            ClienteOtpCode.proposito == "EMAIL_VERIFY",
            ClienteOtpCode.usado == False,
        )
    ).first()
    assert otp is not None

    otp.codigo_hash = hashlib.sha256("123456".encode()).hexdigest()
    db_session.add(otp)
    db_session.commit()

    verify_response = client.post(
        "/api/v1/clientes/auth/verificar-email",
        json={"codigo": "123456"},
        headers=auth_headers,
    )
    assert verify_response.status_code == 200
    db_session.refresh(test_cliente)
    assert test_cliente.email_verificado is True


def test_confirmar_reset_por_otp(client: TestClient, db_session, test_cliente):
    response = client.post(
        "/api/v1/clientes/auth/solicitar-reset",
        json={"email": "cliente@test.com"},
        headers=GATEWAY_HEADER,
    )
    assert response.status_code == 200

    otp = db_session.exec(
        select(ClienteOtpCode).where(
            ClienteOtpCode.cliente_id == test_cliente.id,
            ClienteOtpCode.proposito == "PASSWORD_RESET",
            ClienteOtpCode.usado == False,
        )
    ).first()
    assert otp is not None

    otp.codigo_hash = hashlib.sha256("654321".encode()).hexdigest()
    db_session.add(otp)
    db_session.commit()

    confirm_response = client.post(
        "/api/v1/clientes/auth/confirmar-reset-otp",
        json={
            "email": "cliente@test.com",
            "codigo": "654321",
            "password_nuevo": "NewPassword1",
            "password_nuevo_confirmacion": "NewPassword1",
        },
        headers=GATEWAY_HEADER,
    )
    assert confirm_response.status_code == 200


def test_confirmar_cambio_email_por_otp(client: TestClient, db_session, test_cliente):
    login_response = client.post(
        "/api/v1/clientes/auth/login",
        json={"email": "cliente@test.com", "password_plano": "Password123!"},
        headers=GATEWAY_HEADER,
    )
    token = login_response.json()["access_token"]
    auth_headers = {**GATEWAY_HEADER, "Authorization": f"Bearer {token}"}

    request_response = client.post(
        "/api/v1/clientes/auth/solicitar-cambio-email-otp",
        json={
            "nuevo_email": "nuevo@test.com",
            "password_actual": "Password123!",
        },
        headers=auth_headers,
    )
    assert request_response.status_code == 200

    old_otp = db_session.exec(
        select(ClienteOtpCode).where(
            ClienteOtpCode.cliente_id == test_cliente.id,
            ClienteOtpCode.proposito == "EMAIL_CHANGE_OLD",
            ClienteOtpCode.usado == False,
        )
    ).first()
    new_otp = db_session.exec(
        select(ClienteOtpCode).where(
            ClienteOtpCode.cliente_id == test_cliente.id,
            ClienteOtpCode.proposito == "EMAIL_CHANGE_NEW",
            ClienteOtpCode.usado == False,
        )
    ).first()
    assert old_otp is not None
    assert new_otp is not None

    old_otp.codigo_hash = hashlib.sha256("111111".encode()).hexdigest()
    new_otp.codigo_hash = hashlib.sha256("222222".encode()).hexdigest()
    db_session.add(old_otp)
    db_session.add(new_otp)
    db_session.commit()

    confirm_response = client.post(
        "/api/v1/clientes/auth/confirmar-cambio-email-otp",
        json={
            "codigo_email_actual": "111111",
            "codigo_email_nuevo": "222222",
        },
        headers=auth_headers,
    )
    assert confirm_response.status_code == 200
    db_session.refresh(test_cliente)
    assert test_cliente.email == "nuevo@test.com"
    assert test_cliente.email_verificado is True
