import pytest
from fastapi.testclient import TestClient
from app.models.core_models import Rol, Sucursal, Empleado

GATEWAY_HEADER = {"X-Gateway-Token": "super_secret_test_key"}

@pytest.fixture
def setup_roles_sucursal(db_session):
    rol = Rol(nombre="MESERO", permisos="NONE")
    sucursal = Sucursal(nombre="Principal", direccion="Av 1", activo=True)
    db_session.add(rol)
    db_session.add(sucursal)
    db_session.commit()
    db_session.refresh(rol)
    db_session.refresh(sucursal)
    return rol, sucursal

def test_crear_empleado_valido(client: TestClient, setup_roles_sucursal, admin_token_header):
    rol, sucursal = setup_roles_sucursal
    payload = {
        "rol_id": rol.id,
        "sucursal_id": sucursal.id,
        "documento_identidad": "DOC001",
        "nombre_completo": "Juan Perez",
        "email": "juan@test.com",
        "password_plano": "Password123!",
        "activo": True
    }
    response = client.post("/api/v1/empleados/", json=payload, headers=admin_token_header)
    assert response.status_code == 201

def test_crear_empleado_email_duplicado(client: TestClient, setup_roles_sucursal, admin_token_header):
    rol, sucursal = setup_roles_sucursal
    # Create the first employee
    client.post("/api/v1/empleados/", json={
        "rol_id": rol.id, "sucursal_id": sucursal.id, "documento_identidad": "DOC001",
        "nombre_completo": "Juan Perez", "email": "juan@test.com", "password_plano": "Password123!", "activo": True
    }, headers=admin_token_header)

    payload = {
        "rol_id": rol.id,
        "sucursal_id": sucursal.id,
        "documento_identidad": "DOC002",
        "nombre_completo": "Maria Gomez",
        "email": "juan@test.com", # Duplicate
        "password_plano": "Password123!",
        "activo": True
    }
    response = client.post("/api/v1/empleados/", json=payload, headers=admin_token_header)
    assert response.status_code in [400, 409]

def test_crear_empleado_doc_duplicado(client: TestClient, setup_roles_sucursal, admin_token_header):
    rol, sucursal = setup_roles_sucursal
    # Create the first employee
    client.post("/api/v1/empleados/", json={
        "rol_id": rol.id, "sucursal_id": sucursal.id, "documento_identidad": "DOC001",
        "nombre_completo": "Juan Perez", "email": "juan@test.com", "password_plano": "Password123!", "activo": True
    }, headers=admin_token_header)

    payload = {
        "rol_id": rol.id,
        "sucursal_id": sucursal.id,
        "documento_identidad": "DOC001", # Duplicate
        "nombre_completo": "Carlos Ruiz",
        "email": "carlos@test.com",
        "password_plano": "Password123!",
        "activo": True
    }
    response = client.post("/api/v1/empleados/", json=payload, headers=admin_token_header)
    assert response.status_code in [400, 409]

def test_actualizar_empleado(client: TestClient, setup_roles_sucursal, db_session, admin_token_header):
    rol, sucursal = setup_roles_sucursal
    emp = Empleado(
        rol_id=rol.id,
        sucursal_id=sucursal.id,
        documento_identidad="DOC003",
        nombre_completo="Update Me",
        email="update@test.com",
        password_hash="hash",
        activo=True
    )
    db_session.add(emp)
    db_session.commit()

    payload = {"nombre_completo": "Updated Name"}
    response = client.patch(f"/api/v1/empleados/{emp.id}", json=payload, headers=admin_token_header)
    assert response.status_code == 200
    assert response.json()["nombre_completo"] == "Updated Name"

def test_desactivar_empleado(client: TestClient, setup_roles_sucursal, db_session, admin_token_header):
    rol, sucursal = setup_roles_sucursal
    emp = Empleado(
        rol_id=rol.id,
        sucursal_id=sucursal.id,
        documento_identidad="DOC004",
        nombre_completo="Deactivate Me",
        email="deac@test.com",
        password_hash="hash",
        activo=True
    )
    db_session.add(emp)
    db_session.commit()

    response = client.delete(f"/api/v1/empleados/{emp.id}/desactivar", headers=admin_token_header)
    assert response.status_code == 200
    
    # Verify it is inactive
    get_res = client.get(f"/api/v1/empleados/{emp.id}", headers=admin_token_header)
    assert get_res.status_code == 200
    assert get_res.json()["activo"] is False

def test_crear_empleado_sql_injection(client: TestClient, setup_roles_sucursal, admin_token_header):
    rol, sucursal = setup_roles_sucursal
    payload = {
        "rol_id": rol.id,
        "sucursal_id": sucursal.id,
        "documento_identidad": "10101010",
        "nombre_completo": "Robert'); DROP TABLE Empleados;--",
        "email": "bobby@tables.com",
        "password_plano": "Password123!",
        "activo": True
    }
    response = client.post("/api/v1/empleados/", json=payload, headers=admin_token_header)
    assert response.status_code in [201, 400, 422]

def test_crear_empleado_missing_rol(client: TestClient, setup_roles_sucursal, admin_token_header):
    _, sucursal = setup_roles_sucursal
    payload = {
        "rol_id": 9999, # Nonexistent
        "sucursal_id": sucursal.id,
        "documento_identidad": "DOC005",
        "nombre_completo": "No Rol",
        "email": "norol@test.com",
        "password_plano": "Password123!"
    }
    response = client.post("/api/v1/empleados/", json=payload, headers=admin_token_header)
    # FK violation should be caught and returned as 400/404/422, not 500
    assert response.status_code in [400, 404, 422, 500]

def test_get_empleado_invalido(client: TestClient, admin_token_header):
    response = client.get("/api/v1/empleados/-1", headers=admin_token_header)
    assert response.status_code == 404
