import pytest
from fastapi.testclient import TestClient
from app.models.core_models import Rol, Sucursal

GATEWAY_HEADER = {"X-Gateway-Token": "super_secret_test_key"}

def test_crear_rol(client: TestClient, admin_token_header):
    payload = {"nombre": "NUEVO_ROL"}
    response = client.post("/api/v1/roles/", json=payload, headers=admin_token_header)
    assert response.status_code == 201

def test_crear_rol_duplicado(client: TestClient, db_session, admin_token_header):
    rol = Rol(nombre="ADMIN2")
    db_session.add(rol)
    db_session.commit()

    payload = {"nombre": "ADMIN2"}
    response = client.post("/api/v1/roles/", json=payload, headers=admin_token_header)
    assert response.status_code in [400, 409]

def test_get_roles(client: TestClient):
    response = client.get("/api/v1/roles/", headers=GATEWAY_HEADER)
    assert response.status_code == 200

def test_actualizar_rol(client: TestClient, db_session, admin_token_header):
    rol = Rol(nombre="ROLE_TO_UPDATE")
    db_session.add(rol)
    db_session.commit()
    db_session.refresh(rol)

    payload = {"nombre": "UPDATED_ROLE"}
    response = client.put(f"/api/v1/roles/{rol.id}", json=payload, headers=admin_token_header)
    assert response.status_code == 200
    assert response.json()["nombre"] == "UPDATED_ROLE"

def test_crear_sucursal(client: TestClient, admin_token_header):
    payload = {"nombre": "Sucursal Norte", "direccion": "Calle Falsa 123", "activo": True}
    response = client.post("/api/v1/sucursales/", json=payload, headers=admin_token_header)
    assert response.status_code == 201

def test_get_sucursales(client: TestClient):
    response = client.get("/api/v1/sucursales/", headers=GATEWAY_HEADER)
    assert response.status_code == 200

def test_actualizar_sucursal(client: TestClient, db_session, admin_token_header):
    sucursal = Sucursal(nombre="Sucursal Sur", direccion="Sur 456", activo=True)
    db_session.add(sucursal)
    db_session.commit()
    db_session.refresh(sucursal)

    payload = {"nombre": "Sucursal Sur Actualizada"}
    response = client.put(f"/api/v1/sucursales/{sucursal.id}", json=payload, headers=admin_token_header)
    assert response.status_code == 200
    assert response.json()["nombre"] == "Sucursal Sur Actualizada"

def test_eliminar_sucursal(client: TestClient, db_session, admin_token_header):
    sucursal = Sucursal(nombre="Sucursal a Eliminar", direccion="123", activo=True)
    db_session.add(sucursal)
    db_session.commit()
    db_session.refresh(sucursal)

    response = client.delete(f"/api/v1/sucursales/{sucursal.id}", headers=admin_token_header)
    assert response.status_code == 200
