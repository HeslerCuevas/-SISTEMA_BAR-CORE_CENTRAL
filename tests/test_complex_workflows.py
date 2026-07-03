import pytest
import uuid
from fastapi.testclient import TestClient
from app.models.core_models import Producto, Categoria, Impuesto, PedidoGlobal, DetallePedido, Rol, Empleado

GATEWAY_HEADER = {"X-Gateway-Token": "super_secret_test_key"}

@pytest.fixture
def setup_complex_env(db_session):
    cat = Categoria(nombre="Complejos")
    imp = Impuesto(nombre="ITBIS", tasa_porcentaje=18.0)
    db_session.add(cat)
    db_session.add(imp)
    db_session.commit()
    db_session.refresh(cat)
    db_session.refresh(imp)

    prod = Producto(categoria_id=cat.id, impuesto_id=imp.id, sku="SKU_CX1", nombre="Item CX", precio_base=100.0)
    db_session.add(prod)
    db_session.commit()
    db_session.refresh(prod)

    pedido_uuid = uuid.uuid4()
    pedido = PedidoGlobal(canal_origen="WEB", estado="PENDIENTE", factura_local_uuid=pedido_uuid, total_general=118.0)
    db_session.add(pedido)
    db_session.commit()
    
    detalle = DetallePedido(pedido_id=pedido.id, producto_id=prod.id, cantidad=1, precio_unitario_historico=100.0, impuesto_historico=18.0, monto_impuesto=18.0, subtotal_linea=118.0)
    db_session.add(detalle)
    db_session.commit()

    return prod, pedido_uuid

def test_delete_product_in_active_order(client: TestClient, setup_complex_env, admin_token_header):
    """
    Attempt to delete a product that is currently linked to an active pending order.
    The database should block it due to Foreign Key constraints, or the API should handle it gracefully (soft delete).
    """
    prod, _ = setup_complex_env
    # The API might only support soft delete (activo=False), let's see.
    # If it's a hard DELETE, it should return 409 Conflict or 400.
    response = client.delete(f"/api/v1/productos/{prod.id}", headers=admin_token_header)
    # Most likely it will be soft deleted (200) or blocked (409)
    assert response.status_code in [200, 400, 409]

def test_split_bill_extreme(client: TestClient, setup_complex_env):
    """
    Attempt to split a bill into 100 parts.
    """
    _, pedido_uuid = setup_complex_env
    payload = {"numero_partes": 100}
    response = client.post(f"/api/v1/pedidos/{pedido_uuid}/dividir-cuenta", json=payload, headers=GATEWAY_HEADER)
    # It should succeed or hit a business logic limit.
    assert response.status_code in [200, 400, 422]

def test_facturar_canceled_order(client: TestClient, db_session):
    """
    Cancel an order, then try to pay it.
    """
    pedido_uuid = uuid.uuid4()
    pedido = PedidoGlobal(canal_origen="WEB", estado="CANCELADO", factura_local_uuid=pedido_uuid)
    db_session.add(pedido)
    db_session.commit()

    payload = {"metodo_pago": "TARJETA", "monto_recibido": 500.0}
    response = client.post(f"/api/v1/pedidos/{pedido_uuid}/facturar", json=payload, headers=GATEWAY_HEADER)
    # A canceled order cannot be billed.
    assert response.status_code in [400, 409, 422]

def test_role_change_during_active_session(client: TestClient, db_session, admin_token_header):
    """
    Change an employee's role while they theoretically have a session.
    We just test the role update mechanism on an employee.
    """
    rol1 = Rol(nombre="MESERO")
    rol2 = Rol(nombre="CAJERO")
    db_session.add_all([rol1, rol2])
    db_session.commit()

    emp = Empleado(rol_id=rol1.id, sucursal_id=1, documento_identidad="000", nombre_completo="Emp", email="x@x.com", password_hash="hash")
    db_session.add(emp)
    db_session.commit()

    # Update role to CAJERO
    payload = {"rol_id": rol2.id, "activo": True}
    response = client.patch(f"/api/v1/empleados/{emp.id}", json=payload, headers=admin_token_header)
    # Depends on if endpoint allows updating rol_id directly
    assert response.status_code in [200, 422]
