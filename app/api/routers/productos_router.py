from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, col
from typing import List, Optional
from datetime import datetime

from app.db.database import get_session
from app.models.core_models import Producto, InventarioActual, Impuesto, Categoria
from app.schemas.producto_schema import (
    ProductoCreate, ProductoUpdate, ProductoResponse,
    CategoriaCreate, CategoriaUpdate, CategoriaResponse,
    ImpuestoCreate, ImpuestoUpdate, ImpuestoResponse
)
from app.services.audit_service import log_auditoria
from fastapi.security import HTTPAuthorizationCredentials
from app.core.security import security_bearer, verificar_rol_empleado

router = APIRouter(
    prefix="/api/v1/productos",
    tags=["Módulo de Productos"]
)


@router.get("/", response_model=List[ProductoResponse])
def listar_productos(
    solo_activos: bool = Query(True, description="Filtrar solo productos activos"),
    session: Session = Depends(get_session)
):
    statement = (
        select(
            Producto,
            col(Impuesto.tasa_porcentaje).label("tasa_impuesto"),
            col(InventarioActual.cantidad_disponible).label("cantidad_disponible")
        )
        .join(Impuesto, col(Producto.impuesto_id) == col(Impuesto.id))
        .outerjoin(InventarioActual, col(Producto.id) == col(InventarioActual.producto_id))
    )
    if solo_activos:
        statement = statement.where(col(Producto.activo) == True)

    results = session.exec(statement).all()
    lista_final = []
    for producto, tasa, stock in results:
        p_data = producto.model_dump()
        p_data["tasa_impuesto"] = (tasa / 100) if tasa is not None else 0
        p_data["cantidad_disponible"] = 9999 if not producto.es_inventariable else (stock if stock is not None else 0)
        p_data["categoria_id"] = producto.categoria_id
        lista_final.append(p_data)
    return lista_final


@router.get("/por-categoria/{categoria_id}", response_model=List[ProductoResponse])
def listar_productos_por_categoria(categoria_id: int, session: Session = Depends(get_session)):
    statement = (
        select(
            Producto,
            col(Impuesto.tasa_porcentaje).label("tasa_impuesto"),
            col(InventarioActual.cantidad_disponible).label("cantidad_disponible")
        )
        .join(Impuesto, col(Producto.impuesto_id) == col(Impuesto.id))
        .outerjoin(InventarioActual, col(Producto.id) == col(InventarioActual.producto_id))
        .where(col(Producto.categoria_id) == categoria_id)
        .where(col(Producto.activo) == True)
    )
    results = session.exec(statement).all()
    lista_final = []
    for producto, tasa, stock in results:
        p_data = producto.model_dump()
        p_data["imagen_url"] = producto.imagen_url
        p_data["tasa_impuesto"] = (tasa / 100) if tasa is not None else 0
        p_data["cantidad_disponible"] = 9999 if not producto.es_inventariable else (stock if stock is not None else 0)
        p_data["categoria_id"] = producto.categoria_id
        lista_final.append(p_data)
    return lista_final


@router.post("/", response_model=ProductoResponse, status_code=201)
def crear_producto(
        producto_in: ProductoCreate,
        session: Session = Depends(get_session),
        token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)):

    if not token_obj or not token_obj.credentials:
        raise HTTPException(status_code=401, detail="Token Bearer ausente o inválido")
    verificar_rol_empleado(token_obj.credentials, ["ADMIN", "GERENTE"], session)

    try:
        nuevo_producto = Producto(**producto_in.model_dump())
        session.add(nuevo_producto)
        session.flush()

        if nuevo_producto.es_inventariable:
            nuevo_inventario = InventarioActual(
                producto_id=nuevo_producto.id,
                cantidad_disponible=0,
                stock_minimo=5
            )
            session.add(nuevo_inventario)

        session.commit()
        session.refresh(nuevo_producto)
        return _obtener_producto_response(nuevo_producto.id, session)

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")

# ─────────────────────────────────────────────────────────────────────────────
# CATEGORÍAS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/categorias", response_model=List[CategoriaResponse])
def listar_categorias(
    incluir_inactivas: bool = Query(False),
    session: Session = Depends(get_session)
):
    stmt = select(Categoria)
    if not incluir_inactivas:
        stmt = stmt.where(col(Categoria.activo) == True)
    return session.exec(stmt).all()


@router.get("/categorias/{categoria_id}", response_model=CategoriaResponse)
def obtener_categoria(categoria_id: int, session: Session = Depends(get_session)):
    cat = session.get(Categoria, categoria_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada.")
    return cat


@router.post("/categorias", response_model=CategoriaResponse, status_code=201)
def crear_categoria(
    payload: CategoriaCreate,
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    if not token_obj or not token_obj.credentials:
        raise HTTPException(status_code=401, detail="Token Bearer ausente o inválido")

    verificar_rol_empleado(token_obj.credentials, ["ADMIN", "GERENTE"], session)

    existente = session.exec(select(Categoria).where(Categoria.nombre == payload.nombre)).first()
    if existente:
        raise HTTPException(status_code=400, detail=f"Ya existe una categoría con el nombre '{payload.nombre}'.")

    cat = Categoria(
        nombre=payload.nombre,
        descripcion=payload.descripcion,
        activo=True,
        ultima_modificacion=datetime.utcnow()
    )
    session.add(cat)
    session.commit()
    session.refresh(cat)

    log_auditoria(
        nivel="INFO",
        origen="POST /api/v1/productos/categorias",
        mensaje=f"Categoría creada: '{cat.nombre}' (id={cat.id})",
    )
    return cat


@router.put("/categorias/{categoria_id}", response_model=CategoriaResponse)
def actualizar_categoria(
    categoria_id: int,
    payload: CategoriaUpdate,
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    if not token_obj or not token_obj.credentials:
        raise HTTPException(status_code=401, detail="Token Bearer ausente o inválido")

    verificar_rol_empleado(token_obj.credentials, ["ADMIN", "GERENTE"], session)

    cat = session.get(Categoria, categoria_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada.")

    datos = payload.model_dump(exclude_unset=True)

    if "nombre" in datos and datos["nombre"]:
        dup = session.exec(
            select(Categoria).where(
                Categoria.nombre == datos["nombre"],
                col(Categoria.id) != categoria_id
            )
        ).first()
        if dup:
            raise HTTPException(status_code=400, detail=f"Ya existe otra categoría con el nombre '{datos['nombre']}'.")

    for campo, valor in datos.items():
        setattr(cat, campo, valor)

    cat.ultima_modificacion = datetime.utcnow()
    session.add(cat)
    session.commit()
    session.refresh(cat)

    log_auditoria(
        nivel="INFO",
        origen=f"PUT /api/v1/productos/categorias/{categoria_id}",
        mensaje=f"Categoría actualizada: id={categoria_id}",
        data=datos
    )
    return cat


@router.delete("/categorias/{categoria_id}", response_model=dict)
def desactivar_categoria(
    categoria_id: int,
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    if not token_obj or not token_obj.credentials:
        raise HTTPException(status_code=401, detail="Token Bearer ausente o inválido")

    verificar_rol_empleado(token_obj.credentials, ["ADMIN", "GERENTE"], session)

    cat = session.get(Categoria, categoria_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada.")
    if not cat.activo:
        raise HTTPException(status_code=400, detail="La categoría ya está inactiva.")

    cat.activo = False
    cat.ultima_modificacion = datetime.utcnow()
    session.add(cat)
    session.commit()

    log_auditoria(
        nivel="WARNING",
        origen=f"DELETE /api/v1/productos/categorias/{categoria_id}",
        mensaje=f"Categoría desactivada: id={categoria_id}, nombre='{cat.nombre}'",
    )
    return {"mensaje": f"Categoría '{cat.nombre}' desactivada exitosamente.", "id": categoria_id}


def _obtener_producto_response(producto_id: int, session: Session) -> dict:
    statement = (
        select(
            Producto,
            col(Impuesto.tasa_porcentaje).label("tasa"),
            col(InventarioActual.cantidad_disponible).label("stock")
        )
        .join(Impuesto, col(Producto.impuesto_id) == col(Impuesto.id))
        .outerjoin(InventarioActual, col(Producto.id) == col(InventarioActual.producto_id))
        .where(col(Producto.id) == producto_id)
    )
    result = session.exec(statement).first()
    if not result:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    producto, tasa, stock = result
    p_data = producto.model_dump()
    p_data["tasa_impuesto"] = (tasa / 100) if tasa is not None else 0
    p_data["cantidad_disponible"] = 9999 if not producto.es_inventariable else (stock if stock is not None else 0)
    return p_data


# ─────────────────────────────────────────────────────────────────────────────
# IMPUESTOS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/impuestos", response_model=List[ImpuestoResponse])
def listar_impuestos(
    incluir_inactivos: bool = Query(False),
    session: Session = Depends(get_session)
):
    stmt = select(Impuesto)
    if not incluir_inactivos:
        stmt = stmt.where(col(Impuesto.activo) == True)
    impuestos = session.exec(stmt).all()
    return [
        {"id": i.id, "nombre": i.nombre, "tasa_porcentaje": float(i.tasa_porcentaje), "activo": i.activo}
        for i in impuestos
    ]


@router.get("/impuestos/{impuesto_id}", response_model=ImpuestoResponse)
def obtener_impuesto(impuesto_id: int, session: Session = Depends(get_session)):
    imp = session.get(Impuesto, impuesto_id)
    if not imp:
        raise HTTPException(status_code=404, detail="Impuesto no encontrado.")
    return {"id": imp.id, "nombre": imp.nombre, "tasa_porcentaje": float(imp.tasa_porcentaje), "activo": imp.activo}


@router.post("/impuestos", response_model=ImpuestoResponse, status_code=201)
def crear_impuesto(
    payload: ImpuestoCreate,
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    if not token_obj or not token_obj.credentials:
        raise HTTPException(status_code=401, detail="Token Bearer ausente o inválido")

    verificar_rol_empleado(token_obj.credentials, ["ADMIN", "GERENTE"], session)

    existente = session.exec(select(Impuesto).where(Impuesto.nombre == payload.nombre)).first()
    if existente:
        raise HTTPException(status_code=400, detail=f"Ya existe un impuesto con el nombre '{payload.nombre}'.")

    imp = Impuesto(
        nombre=payload.nombre,
        tasa_porcentaje=payload.tasa_porcentaje,
        activo=True,
        ultima_modificacion=datetime.utcnow()
    )
    session.add(imp)
    session.commit()
    session.refresh(imp)

    log_auditoria(
        nivel="INFO",
        origen="POST /api/v1/productos/impuestos",
        mensaje=f"Impuesto creado: '{imp.nombre}' ({imp.tasa_porcentaje}%) id={imp.id}",
    )
    return {"id": imp.id, "nombre": imp.nombre, "tasa_porcentaje": float(imp.tasa_porcentaje), "activo": imp.activo}


@router.put("/impuestos/{impuesto_id}", response_model=ImpuestoResponse)
def actualizar_impuesto(
    impuesto_id: int,
    payload: ImpuestoUpdate,
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    if not token_obj or not token_obj.credentials:
        raise HTTPException(status_code=401, detail="Token Bearer ausente o inválido")

    verificar_rol_empleado(token_obj.credentials, ["ADMIN", "GERENTE"], session)

    imp = session.get(Impuesto, impuesto_id)
    if not imp:
        raise HTTPException(status_code=404, detail="Impuesto no encontrado.")

    datos = payload.model_dump(exclude_unset=True)

    if "nombre" in datos and datos["nombre"]:
        dup = session.exec(
            select(Impuesto).where(
                Impuesto.nombre == datos["nombre"],
                col(Impuesto.id) != impuesto_id
            )
        ).first()
        if dup:
            raise HTTPException(status_code=400, detail=f"Ya existe otro impuesto con el nombre '{datos['nombre']}'.")

    for campo, valor in datos.items():
        setattr(imp, campo, valor)

    imp.ultima_modificacion = datetime.utcnow()
    session.add(imp)
    session.commit()
    session.refresh(imp)

    log_auditoria(
        nivel="INFO",
        origen=f"PUT /api/v1/productos/impuestos/{impuesto_id}",
        mensaje=f"Impuesto actualizado: id={impuesto_id}",
        data=datos
    )
    return {"id": imp.id, "nombre": imp.nombre, "tasa_porcentaje": float(imp.tasa_porcentaje), "activo": imp.activo}


@router.delete("/impuestos/{impuesto_id}", response_model=dict)
def desactivar_impuesto(
    impuesto_id: int,
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    if not token_obj or not token_obj.credentials:
        raise HTTPException(status_code=401, detail="Token Bearer ausente o inválido")

    verificar_rol_empleado(token_obj.credentials, ["ADMIN"], session)

    imp = session.get(Impuesto, impuesto_id)
    if not imp:
        raise HTTPException(status_code=404, detail="Impuesto no encontrado.")
    if not imp.activo:
        raise HTTPException(status_code=400, detail="El impuesto ya está inactivo.")

    # Verificar que no haya productos activos con este impuesto
    productos_con_impuesto = session.exec(
        select(Producto).where(
            col(Producto.impuesto_id) == impuesto_id,
            col(Producto.activo) == True
        )
    ).first()
    if productos_con_impuesto:
        raise HTTPException(
            status_code=409,
            detail="No se puede desactivar el impuesto porque hay productos activos que lo usan. "
                   "Reasigna los productos a otro impuesto primero."
        )

    imp.activo = False
    imp.ultima_modificacion = datetime.utcnow()
    session.add(imp)
    session.commit()

    log_auditoria(
        nivel="WARNING",
        origen=f"DELETE /api/v1/productos/impuestos/{impuesto_id}",
        mensaje=f"Impuesto desactivado: id={impuesto_id}, nombre='{imp.nombre}'",
    )
    return {"mensaje": f"Impuesto '{imp.nombre}' desactivado exitosamente.", "id": impuesto_id}



@router.get("/{producto_id}", response_model=ProductoResponse)
def obtener_producto(producto_id: int, session: Session = Depends(get_session)):
    return _obtener_producto_response(producto_id, session)


@router.patch("/{producto_id}", response_model=ProductoResponse)
def actualizar_producto_parcial(
    producto_id: int,
    payload: ProductoUpdate,
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    if not token_obj or not token_obj.credentials:
        raise HTTPException(status_code=401, detail="Token Bearer ausente o inválido")

    """PATCH — actualización parcial. Solo se modifican los campos enviados."""
    verificar_rol_empleado(token_obj.credentials, ["ADMIN", "GERENTE"], session)

    producto = session.get(Producto, producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")

    datos = payload.model_dump(exclude_unset=True)

    if "categoria_id" in datos:
        cat = session.get(Categoria, datos["categoria_id"])
        if not cat or not cat.activo:
            raise HTTPException(status_code=404, detail=f"Categoría id={datos['categoria_id']} no existe o está inactiva.")

    if "impuesto_id" in datos:
        imp = session.get(Impuesto, datos["impuesto_id"])
        if not imp or not imp.activo:
            raise HTTPException(status_code=404, detail=f"Impuesto id={datos['impuesto_id']} no existe o está inactivo.")

    for campo, valor in datos.items():
        setattr(producto, campo, valor)

    producto.ultima_modificacion = datetime.utcnow()
    session.add(producto)
    session.commit()

    log_auditoria(
        nivel="INFO",
        origen=f"PATCH /api/v1/productos/{producto_id}",
        mensaje=f"Producto id={producto_id} actualizado parcialmente.",
        data=datos
    )
    return _obtener_producto_response(producto_id, session)


@router.delete("/{producto_id}", response_model=dict)
def desactivar_producto(
    producto_id: int,
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    if not token_obj or not token_obj.credentials:
        raise HTTPException(status_code=401, detail="Token Bearer ausente o inválido")

    """Baja lógica del producto. No se elimina físicamente para conservar historial."""
    verificar_rol_empleado(token_obj.credentials, ["ADMIN", "GERENTE"], session)

    producto = session.get(Producto, producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")
    if not producto.activo:
        raise HTTPException(status_code=400, detail="El producto ya está inactivo.")

    producto.activo = False
    producto.ultima_modificacion = datetime.utcnow()
    session.add(producto)
    session.commit()

    log_auditoria(
        nivel="WARNING",
        origen=f"DELETE /api/v1/productos/{producto_id}",
        mensaje=f"Producto desactivado (baja lógica): id={producto_id}, SKU={producto.sku}",
    )
    return {
        "mensaje": f"Producto '{producto.nombre}' desactivado. El historial de pedidos y facturación se conserva.",
        "id": producto_id,
        "activo": False
    }

