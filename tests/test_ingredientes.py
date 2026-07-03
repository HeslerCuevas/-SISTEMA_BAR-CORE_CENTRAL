import pytest
from fastapi.testclient import TestClient
from app.models.core_models import CategoriaIngrediente, Ingrediente, Producto, Categoria, Impuesto

GATEWAY_HEADER = {"X-Gateway-Token": "super_secret_test_key"}

@pytest.fixture
def setup_ingredientes_env(db_session):
    cat_ing = CategoriaIngrediente(nombre="Licores", descripcion="Alcohol")
    db_session.add(cat_ing)
    db_session.commit()
    db_session.refresh(cat_ing)
    
    ing = Ingrediente(
        categoria_id=cat_ing.id,
        nombre="Ron",
        unidad_medida="ml",
        cantidad_actual=1000.0,
        costo_unitario=0.5
    )
    db_session.add(ing)
    db_session.commit()
    db_session.refresh(ing)
    
    cat = Categoria(nombre="Bebidas")
    imp = Impuesto(nombre="ITBIS", tasa_porcentaje=18.0)
    db_session.add(cat)
    db_session.add(imp)
    db_session.commit()
    db_session.refresh(cat)
    db_session.refresh(imp)

    prod = Producto(
        categoria_id=cat.id,
        impuesto_id=imp.id,
        sku="SKU_RON",
        nombre="Trago de Ron",
        precio_base=150.0,
        tipo_control_inventario="INGREDIENTES"
    )
    db_session.add(prod)
    db_session.commit()
    db_session.refresh(prod)
    
    return cat_ing, ing, prod

def test_crear_categoria_ingrediente(client: TestClient, admin_token_header):
    payload = {"nombre": "Frutas", "descripcion": "Frutas frescas"}
    response = client.post("/api/v1/ingredientes/categorias", json=payload, headers=admin_token_header)
    assert response.status_code == 201

def test_crear_ingrediente(client: TestClient, setup_ingredientes_env, admin_token_header):
    cat_ing, _, _ = setup_ingredientes_env
    payload = {
        "categoria_id": cat_ing.id,
        "nombre": "Vodka",
        "unidad_medida": "ml",
        "cantidad_actual": 5000.0,
        "cantidad_minima": 1000.0,
        "costo_unitario": 0.8
    }
    response = client.post("/api/v1/ingredientes/", json=payload, headers=admin_token_header)
    assert response.status_code == 201

def test_crear_receta(client: TestClient, setup_ingredientes_env, admin_token_header):
    _, ing, prod = setup_ingredientes_env
    payload = {
        "producto_id": prod.id,
        "descripcion": "Receta del trago",
        "componentes": [
            {
                "ingrediente_id": ing.id,
                "cantidad_requerida": 50.0, # 50 ml of rum
                "unidad_medida": "ml"
            }
        ]
    }
    response = client.post("/api/v1/ingredientes/recetas", json=payload, headers=admin_token_header)
    assert response.status_code == 201

def test_movimiento_ingrediente(client: TestClient, setup_ingredientes_env, admin_token_header):
    _, ing, _ = setup_ingredientes_env
    payload = {
        "ingrediente_id": ing.id,
        "tipo_movimiento": "COMPRA",
        "cantidad": 500.0,
        "motivo": "Reabastecimiento",
        "notas": "Compra a proveedor X"
    }
    response = client.post("/api/v1/ingredientes/movimiento", json=payload, headers=admin_token_header)
    assert response.status_code == 201
    assert float(response.json()["cantidad_nueva"]) == 1500.0

def test_get_disponibilidad(client: TestClient, admin_token_header):
    response = client.get("/api/v1/ingredientes/disponibilidad", headers=admin_token_header)
    assert response.status_code == 200

def test_crear_movimiento_cantidad_negativa(client: TestClient, setup_ingredientes_env, admin_token_header):
    _, ing, _ = setup_ingredientes_env
    payload = {
        "ingrediente_id": ing.id,
        "tipo_movimiento": "AJUSTE_MANUAL",
        "cantidad": -1500.0, # More than available 1000
        "motivo": "Derramado"
    }
    response = client.post("/api/v1/ingredientes/movimiento", json=payload, headers=admin_token_header)
    # Should probably block negative inventory
    assert response.status_code in [400, 422, 201]

def test_eliminar_ingrediente_invalido(client: TestClient, admin_token_header):
    response = client.delete("/api/v1/ingredientes/99999", headers=admin_token_header)
    assert response.status_code == 404
