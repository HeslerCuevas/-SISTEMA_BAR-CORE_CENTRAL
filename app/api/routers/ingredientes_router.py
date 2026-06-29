from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials
from sqlmodel import Session, col, select

from app.core.security import security_bearer, verificar_rol_empleado
from app.db.database import get_session
from app.logic.ingredient_inventory_manager import IngredientInventoryManager
from app.models.core_models import (
    CategoriaIngrediente,
    ComponenteReceta,
    Ingrediente,
    MovimientoIngrediente,
    Producto,
    RecetaProducto,
)
from app.schemas.ingredientes_schema import (
    CategoriaIngredienteCreate,
    CategoriaIngredienteResponse,
    CategoriaIngredienteUpdate,
    ComponenteRecetaResponse,
    DisponibilidadProductoResponse,
    IngredienteCreate,
    IngredienteResponse,
    IngredienteUpdate,
    MovimientoIngredienteCreate,
    MovimientoIngredienteResponse,
    RecetaProductoCreate,
    RecetaProductoResponse,
)
from app.services.audit_service import log_auditoria

router = APIRouter(
    prefix="/api/v1/ingredientes",
    tags=["Módulo de Ingredientes"],
)


@router.get("/categorias", response_model=List[CategoriaIngredienteResponse])
def listar_categorias_ingredientes(
    incluir_inactivas: bool = Query(False),
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
):
    verificar_rol_empleado(token_obj.credentials if token_obj else None, ["ADMIN", "GERENTE", "INVENTARIO"], session)
    stmt = select(CategoriaIngrediente)
    if not incluir_inactivas:
        stmt = stmt.where(col(CategoriaIngrediente.activo) == True)
    return session.exec(stmt).all()


@router.get("/categorias/{categoria_id}", response_model=CategoriaIngredienteResponse)
def obtener_categoria_ingrediente(
    categoria_id: int,
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
):
    verificar_rol_empleado(token_obj.credentials if token_obj else None, ["ADMIN", "GERENTE", "INVENTARIO"], session)
    cat = session.get(CategoriaIngrediente, categoria_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Categoría de ingrediente no encontrada.")
    return cat


@router.post("/categorias", response_model=CategoriaIngredienteResponse, status_code=201)
def crear_categoria_ingrediente(
    payload: CategoriaIngredienteCreate,
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
):
    verificar_rol_empleado(token_obj.credentials if token_obj else None, ["ADMIN", "GERENTE"], session)

    existente = session.exec(
        select(CategoriaIngrediente).where(CategoriaIngrediente.nombre == payload.nombre)
    ).first()
    if existente:
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe una categoría de ingrediente con el nombre '{payload.nombre}'.",
        )

    cat = CategoriaIngrediente(
        nombre=payload.nombre,
        descripcion=payload.descripcion,
        activo=True,
        ultima_modificacion=datetime.utcnow(),
    )
    session.add(cat)
    session.commit()
    session.refresh(cat)

    log_auditoria(
        nivel="INFO",
        origen="POST /api/v1/ingredientes/categorias",
        mensaje=f"Categoría de ingrediente creada: '{cat.nombre}' (id={cat.id})",
    )
    return cat


@router.put("/categorias/{categoria_id}", response_model=CategoriaIngredienteResponse)
def actualizar_categoria_ingrediente(
    categoria_id: int,
    payload: CategoriaIngredienteUpdate,
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
):
    verificar_rol_empleado(token_obj.credentials if token_obj else None, ["ADMIN", "GERENTE"], session)

    cat = session.get(CategoriaIngrediente, categoria_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Categoría de ingrediente no encontrada.")

    datos = payload.model_dump(exclude_unset=True)

    if "nombre" in datos and datos["nombre"]:
        dup = session.exec(
            select(CategoriaIngrediente).where(
                CategoriaIngrediente.nombre == datos["nombre"],
                col(CategoriaIngrediente.id) != categoria_id,
            )
        ).first()
        if dup:
            raise HTTPException(
                status_code=400,
                detail=f"Ya existe otra categoría con el nombre '{datos['nombre']}'.",
            )

    for campo, valor in datos.items():
        setattr(cat, campo, valor)

    cat.ultima_modificacion = datetime.utcnow()
    session.add(cat)
    session.commit()
    session.refresh(cat)

    log_auditoria(
        nivel="INFO",
        origen=f"PUT /api/v1/ingredientes/categorias/{categoria_id}",
        mensaje=f"Categoría de ingrediente actualizada: id={categoria_id}",
        data=datos,
    )
    return cat


@router.delete("/categorias/{categoria_id}", response_model=dict)
def desactivar_categoria_ingrediente(
    categoria_id: int,
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
):
    verificar_rol_empleado(token_obj.credentials if token_obj else None, ["ADMIN"], session)

    cat = session.get(CategoriaIngrediente, categoria_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Categoría de ingrediente no encontrada.")
    if not cat.activo:
        raise HTTPException(status_code=400, detail="La categoría ya está inactiva.")

    ingrediente_activo = session.exec(
        select(Ingrediente).where(
            col(Ingrediente.categoria_id) == categoria_id,
            col(Ingrediente.activo) == True,
        )
    ).first()
    if ingrediente_activo:
        raise HTTPException(
            status_code=409,
            detail="No se puede desactivar la categoría porque tiene ingredientes activos. "
                   "Reasigna o desactiva los ingredientes primero.",
        )

    cat.activo = False
    cat.ultima_modificacion = datetime.utcnow()
    session.add(cat)
    session.commit()

    log_auditoria(
        nivel="WARNING",
        origen=f"DELETE /api/v1/ingredientes/categorias/{categoria_id}",
        mensaje=f"Categoría de ingrediente desactivada: id={categoria_id}, nombre='{cat.nombre}'",
    )
    return {"mensaje": f"Categoría '{cat.nombre}' desactivada exitosamente.", "id": categoria_id}


# ─────────────────────────────────────────────────────────────────────────────
# DISPONIBILIDAD DE PRODUCTOS (calculated from ingredient stock)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/disponibilidad", response_model=List[DisponibilidadProductoResponse])
def listar_disponibilidad_productos(
    solo_activos: bool = Query(True),
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
):
    """
    Returns calculated product availability for ALL products.
    INGREDIENTES products: computed from ingredient stock via BOM.
    PRODUCTO products: shows legacy InventarioActual stock.
    NINGUNO products: null (not tracked).
    """
    verificar_rol_empleado(token_obj.credentials if token_obj else None, [], session)

    stmt = select(Producto)
    if solo_activos:
        stmt = stmt.where(col(Producto.activo) == True)
    productos = session.exec(stmt).all()

    resultado = []
    for producto in productos:
        tipo = getattr(producto, "tipo_control_inventario", "PRODUCTO")

        if tipo == "NINGUNO":
            disp = {
                "cantidad_producible": None,
                "ingrediente_limitante": None,
                "tiene_receta": False,
            }
        elif tipo == "INGREDIENTES":
            disp = IngredientInventoryManager.calcular_disponibilidad_producto(
                session, producto.id
            )
        else:
            # PRODUCTO — legacy stock, availability not computed here
            disp = {
                "cantidad_producible": None,
                "ingrediente_limitante": None,
                "tiene_receta": False,
            }

        resultado.append(
            DisponibilidadProductoResponse(
                producto_id=producto.id,
                producto_nombre=producto.nombre,
                tipo_control_inventario=tipo,
                cantidad_producible=disp["cantidad_producible"],
                ingrediente_limitante=disp.get("ingrediente_limitante"),
                tiene_receta=disp.get("tiene_receta", False),
            )
        )

    return resultado


@router.get("/disponibilidad/{producto_id}", response_model=DisponibilidadProductoResponse)
def obtener_disponibilidad_producto(
    producto_id: int,
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
):
    """
    Calculate and return the producible quantity for a single INGREDIENTES product.
    """
    verificar_rol_empleado(token_obj.credentials if token_obj else None, [], session)

    producto = session.get(Producto, producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")

    tipo = getattr(producto, "tipo_control_inventario", "PRODUCTO")

    if tipo == "NINGUNO":
        disp = {"cantidad_producible": None, "ingrediente_limitante": None, "tiene_receta": False}
    elif tipo == "INGREDIENTES":
        disp = IngredientInventoryManager.calcular_disponibilidad_producto(session, producto_id)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"El producto '{producto.nombre}' usa control de inventario tipo '{tipo}'. "
                   f"La disponibilidad por ingredientes solo aplica a productos tipo INGREDIENTES.",
        )

    return DisponibilidadProductoResponse(
        producto_id=producto.id,
        producto_nombre=producto.nombre,
        tipo_control_inventario=tipo,
        cantidad_producible=disp["cantidad_producible"],
        ingrediente_limitante=disp.get("ingrediente_limitante"),
        tiene_receta=disp.get("tiene_receta", False),
    )


# ─────────────────────────────────────────────────────────────────────────────
# MOVIMIENTOS MANUALES DE INGREDIENTES
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/movimiento", response_model=MovimientoIngredienteResponse, status_code=201)
def registrar_movimiento_ingrediente(
    mov_in: MovimientoIngredienteCreate,
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
):
    """
    Record a manual ingredient stock movement.

    Allowed types (manual only):
        COMPRA, AJUSTE_MANUAL, DESPERDICIO, CORRECCION, CARGA_INICIAL

    For CORRECCION: *cantidad* is the new absolute stock level.
    For all others: *cantidad* is the positive quantity delta.
    """
    empleado_info = verificar_rol_empleado(
        token_obj.credentials if token_obj else None, ["ADMIN", "GERENTE", "INVENTARIO"], session
    )

    try:
        ingrediente, movimiento = IngredientInventoryManager.registrar_movimiento_ingrediente(
            session=session,
            ingrediente_id=mov_in.ingrediente_id,
            tipo=mov_in.tipo_movimiento,
            cantidad=mov_in.cantidad,
            empleado_id=empleado_info["empleado_id"],
            notas=mov_in.notas,
            documento_referencia=mov_in.documento_referencia,
            movimiento_local_uuid=mov_in.movimiento_local_uuid,
        )
        session.commit()
        session.refresh(movimiento)

        log_auditoria(
            nivel="INFO",
            origen="POST /api/v1/ingredientes/movimiento",
            mensaje=(
                f"Movimiento {mov_in.tipo_movimiento} de {mov_in.cantidad} "
                f"unidades registrado para ingrediente id={mov_in.ingrediente_id}."
            ),
            data=mov_in.model_dump(),
        )

        return movimiento

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# RECETAS / BOM
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/recetas", response_model=RecetaProductoResponse, status_code=201)
def crear_o_reemplazar_receta(
    payload: RecetaProductoCreate,
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
):
    """
    Create or completely replace the recipe (BOM) for a product.

    If a recipe already exists for the product, all its components are deleted
    and replaced with the new list (upsert semantics).

    The product's tipo_control_inventario is automatically set to INGREDIENTES.
    """
    verificar_rol_empleado(token_obj.credentials if token_obj else None, ["ADMIN", "GERENTE"], session)

    # Validate product exists
    producto = session.get(Producto, payload.producto_id)
    if not producto or not producto.activo:
        raise HTTPException(
            status_code=404,
            detail=f"Producto id={payload.producto_id} no encontrado o está inactivo.",
        )

    # Validate all ingredients exist and are active
    for comp in payload.componentes:
        ing = session.get(Ingrediente, comp.ingrediente_id)
        if not ing:
            raise HTTPException(
                status_code=404,
                detail=f"Ingrediente id={comp.ingrediente_id} no encontrado.",
            )
        if not ing.activo:
            raise HTTPException(
                status_code=400,
                detail=f"El ingrediente '{ing.nombre}' (id={ing.id}) está inactivo.",
            )
        # Validate unit compatibility
        from app.logic.unit_converter import are_compatible
        if not are_compatible(comp.unidad_medida, ing.unidad_medida):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"La unidad '{comp.unidad_medida}' de la receta es incompatible con la unidad "
                    f"'{ing.unidad_medida}' del ingrediente '{ing.nombre}'. "
                    f"Solo se permiten conversiones dentro de la misma familia."
                ),
            )

    try:
        # Upsert recipe header
        receta = session.exec(
            select(RecetaProducto).where(RecetaProducto.producto_id == payload.producto_id)
        ).first()

        if receta:
            # Delete existing components
            componentes_existentes = session.exec(
                select(ComponenteReceta).where(ComponenteReceta.receta_id == receta.id)
            ).all()
            for comp_existente in componentes_existentes:
                session.delete(comp_existente)
            session.flush()

            receta.descripcion = payload.descripcion
            receta.activo = True
            receta.ultima_modificacion = datetime.utcnow()
        else:
            receta = RecetaProducto(
                producto_id=payload.producto_id,
                descripcion=payload.descripcion,
                activo=True,
                ultima_modificacion=datetime.utcnow(),
            )
            session.add(receta)
            session.flush()

        # Insert new components
        for comp_data in payload.componentes:
            comp = ComponenteReceta(
                receta_id=receta.id,
                ingrediente_id=comp_data.ingrediente_id,
                cantidad_requerida=comp_data.cantidad_requerida,
                unidad_medida=comp_data.unidad_medida,
            )
            session.add(comp)

        # Automatically upgrade product to INGREDIENTES control type
        producto.tipo_control_inventario = "INGREDIENTES"
        producto.ultima_modificacion = datetime.utcnow()
        session.add(producto)

        session.commit()
        session.refresh(receta)

        # Build response with component details
        componentes = session.exec(
            select(ComponenteReceta).where(ComponenteReceta.receta_id == receta.id)
        ).all()
        componentes_response = []
        for c in componentes:
            ing = session.get(Ingrediente, c.ingrediente_id)
            componentes_response.append(
                ComponenteRecetaResponse(
                    id=c.id,
                    ingrediente_id=c.ingrediente_id,
                    ingrediente_nombre=ing.nombre if ing else "Desconocido",
                    cantidad_requerida=c.cantidad_requerida,
                    unidad_medida=c.unidad_medida,
                )
            )

        log_auditoria(
            nivel="INFO",
            origen="POST /api/v1/ingredientes/recetas",
            mensaje=f"Receta creada/reemplazada para producto id={payload.producto_id}",
            data={"producto_id": payload.producto_id, "num_componentes": len(componentes_response)},
        )

        return RecetaProductoResponse(
            id=receta.id,
            producto_id=receta.producto_id,
            descripcion=receta.descripcion,
            activo=receta.activo,
            ultima_modificacion=receta.ultima_modificacion,
            componentes=componentes_response,
        )

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error al guardar la receta: {str(e)}")


@router.get("/recetas/{producto_id}", response_model=RecetaProductoResponse)
def obtener_receta_producto(
    producto_id: int,
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
):
    verificar_rol_empleado(token_obj.credentials if token_obj else None, [], session)

    receta = session.exec(
        select(RecetaProducto).where(RecetaProducto.producto_id == producto_id)
    ).first()
    if not receta:
        raise HTTPException(
            status_code=404,
            detail=f"El producto id={producto_id} no tiene receta configurada.",
        )

    componentes = session.exec(
        select(ComponenteReceta).where(ComponenteReceta.receta_id == receta.id)
    ).all()
    componentes_response = []
    for c in componentes:
        ing = session.get(Ingrediente, c.ingrediente_id)
        componentes_response.append(
            ComponenteRecetaResponse(
                id=c.id,
                ingrediente_id=c.ingrediente_id,
                ingrediente_nombre=ing.nombre if ing else "Desconocido",
                cantidad_requerida=c.cantidad_requerida,
                unidad_medida=c.unidad_medida,
            )
        )

    return RecetaProductoResponse(
        id=receta.id,
        producto_id=receta.producto_id,
        descripcion=receta.descripcion,
        activo=receta.activo,
        ultima_modificacion=receta.ultima_modificacion,
        componentes=componentes_response,
    )


@router.delete("/recetas/{producto_id}", response_model=dict)
def eliminar_receta_producto(
    producto_id: int,
    revertir_tipo_control: bool = Query(
        True, description="Si True, revierte el tipo de control a PRODUCTO"
    ),
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
):
    """
    Soft-delete a product's recipe by deactivating it.
    Optionally reverts the product's tipo_control_inventario to PRODUCTO.
    """
    verificar_rol_empleado(token_obj.credentials if token_obj else None, ["ADMIN"], session)

    receta = session.exec(
        select(RecetaProducto).where(RecetaProducto.producto_id == producto_id)
    ).first()
    if not receta:
        raise HTTPException(
            status_code=404,
            detail=f"El producto id={producto_id} no tiene receta configurada.",
        )

    receta.activo = False
    receta.ultima_modificacion = datetime.utcnow()
    session.add(receta)

    if revertir_tipo_control:
        producto = session.get(Producto, producto_id)
        if producto:
            producto.tipo_control_inventario = "PRODUCTO"
            producto.ultima_modificacion = datetime.utcnow()
            session.add(producto)

    session.commit()

    log_auditoria(
        nivel="WARNING",
        origen=f"DELETE /api/v1/ingredientes/recetas/{producto_id}",
        mensaje=f"Receta desactivada para producto id={producto_id}",
    )
    return {
        "mensaje": f"Receta del producto id={producto_id} desactivada.",
        "tipo_control_revertido": revertir_tipo_control,
    }


# ─────────────────────────────────────────────────────────────────────────────
# INGREDIENTES — CRUD
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[IngredienteResponse])
def listar_ingredientes(
    solo_activos: bool = Query(True),
    categoria_id: Optional[int] = Query(None),
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
):
    verificar_rol_empleado(token_obj.credentials if token_obj else None, ["ADMIN", "GERENTE", "INVENTARIO"], session)

    stmt = select(Ingrediente)
    if solo_activos:
        stmt = stmt.where(col(Ingrediente.activo) == True)
    if categoria_id:
        stmt = stmt.where(col(Ingrediente.categoria_id) == categoria_id)

    ingredientes = session.exec(stmt).all()
    return [IngredienteResponse.from_orm_with_alert(ing) for ing in ingredientes]


@router.post("/", response_model=IngredienteResponse, status_code=201)
def crear_ingrediente(
    payload: IngredienteCreate,
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
):
    verificar_rol_empleado(token_obj.credentials if token_obj else None, ["ADMIN", "GERENTE"], session)

    # Validate category exists and is active
    cat = session.get(CategoriaIngrediente, payload.categoria_id)
    if not cat or not cat.activo:
        raise HTTPException(
            status_code=404,
            detail=f"Categoría de ingrediente id={payload.categoria_id} no encontrada o inactiva.",
        )

    try:
        ing = Ingrediente(
            categoria_id=payload.categoria_id,
            nombre=payload.nombre,
            descripcion=payload.descripcion,
            unidad_medida=payload.unidad_medida,
            cantidad_actual=payload.cantidad_actual,
            cantidad_minima=payload.cantidad_minima,
            cantidad_reorden=payload.cantidad_reorden,
            costo_unitario=payload.costo_unitario,
            activo=True,
            ultima_modificacion=datetime.utcnow(),
        )
        session.add(ing)
        session.commit()
        session.refresh(ing)

        # If initial stock > 0, create a CARGA_INICIAL movement for traceability
        if payload.cantidad_actual > 0:
            from app.logic.ingredient_inventory_manager import IngredientInventoryManager as IIM
            movimiento = MovimientoIngrediente(
                ingrediente_id=ing.id,
                tipo_movimiento="CARGA_INICIAL",
                cantidad=payload.cantidad_actual,
                cantidad_anterior=Decimal("0"),
                cantidad_nueva=payload.cantidad_actual,
                notas="Stock inicial al crear el ingrediente.",
            )
            session.add(movimiento)
            session.commit()

        log_auditoria(
            nivel="INFO",
            origen="POST /api/v1/ingredientes/",
            mensaje=f"Ingrediente creado: '{ing.nombre}' (id={ing.id})",
            data=payload.model_dump(),
        )
        return IngredienteResponse.from_orm_with_alert(ing)

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=f"Error al crear ingrediente: {str(e)}")


@router.patch("/{ingrediente_id}", response_model=IngredienteResponse)
def actualizar_ingrediente(
    ingrediente_id: int,
    payload: IngredienteUpdate,
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
):
    verificar_rol_empleado(token_obj.credentials if token_obj else None, ["ADMIN", "GERENTE"], session)

    ing = session.get(Ingrediente, ingrediente_id)
    if not ing:
        raise HTTPException(status_code=404, detail="Ingrediente no encontrado.")

    # exclude_unset=True makes this a true partial update (PATCH)
    datos = payload.model_dump(exclude_unset=True)

    if "categoria_id" in datos:
        cat = session.get(CategoriaIngrediente, datos["categoria_id"])
        if not cat or not cat.activo:
            raise HTTPException(
                status_code=404,
                detail=f"Categoría id={datos['categoria_id']} no encontrada o inactiva.",
            )

    # Prevent changing unit if there are existing movements (would corrupt history)
    if "unidad_medida" in datos and datos["unidad_medida"] != ing.unidad_medida:
        tiene_movimientos = session.exec(
            select(MovimientoIngrediente).where(
                MovimientoIngrediente.ingrediente_id == ingrediente_id
            )
        ).first()
        if tiene_movimientos:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"No se puede cambiar la unidad de '{ing.nombre}' porque ya tiene "
                    f"movimientos registrados en '{ing.unidad_medida}'. "
                    f"Crea un nuevo ingrediente si necesitas otra unidad."
                ),
            )

    for campo, valor in datos.items():
        setattr(ing, campo, valor)

    ing.ultima_modificacion = datetime.utcnow()
    session.add(ing)
    session.commit()
    session.refresh(ing)

    log_auditoria(
        nivel="INFO",
        origen=f"PATCH /api/v1/ingredientes/{ingrediente_id}",
        mensaje=f"Ingrediente actualizado: id={ingrediente_id}",
        data=datos,
    )
    return IngredienteResponse.from_orm_with_alert(ing)

@router.delete("/{ingrediente_id}", response_model=dict)
def desactivar_ingrediente(
    ingrediente_id: int,
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
):
    verificar_rol_empleado(token_obj.credentials if token_obj else None, ["ADMIN"], session)

    ing = session.get(Ingrediente, ingrediente_id)
    if not ing:
        raise HTTPException(status_code=404, detail="Ingrediente no encontrado.")
    if not ing.activo:
        raise HTTPException(status_code=400, detail="El ingrediente ya está inactivo.")

    # Verify no active recipes reference this ingredient
    comp_activo = session.exec(
        select(ComponenteReceta).where(
            col(ComponenteReceta.ingrediente_id) == ingrediente_id
        )
    ).first()
    if comp_activo:
        raise HTTPException(
            status_code=409,
            detail=(
                f"No se puede desactivar '{ing.nombre}' porque está siendo usado en una o más "
                f"recetas activas. Elimina el ingrediente de las recetas primero."
            ),
        )

    ing.activo = False
    ing.ultima_modificacion = datetime.utcnow()
    session.add(ing)
    session.commit()

    log_auditoria(
        nivel="WARNING",
        origen=f"DELETE /api/v1/ingredientes/{ingrediente_id}",
        mensaje=f"Ingrediente desactivado: id={ingrediente_id}, nombre='{ing.nombre}'",
    )
    return {"mensaje": f"Ingrediente '{ing.nombre}' desactivado.", "id": ingrediente_id}


@router.get("/{ingrediente_id}", response_model=IngredienteResponse)
def obtener_ingrediente(
    ingrediente_id: int,
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
):
    verificar_rol_empleado(token_obj.credentials if token_obj else None, [], session)

    ing = session.get(Ingrediente, ingrediente_id)
    if not ing:
        raise HTTPException(status_code=404, detail="Ingrediente no encontrado.")
    return IngredienteResponse.from_orm_with_alert(ing)


@router.get("/{ingrediente_id}/movimientos", response_model=List[MovimientoIngredienteResponse])
def listar_movimientos_ingrediente(
    ingrediente_id: int,
    limite: int = Query(50, ge=1, le=500, description="Máximo de registros a retornar"),
    tipo: Optional[str] = Query(None, description="Filtrar por tipo de movimiento"),
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
):
    """
    Return the movement history (ledger) for a single ingredient, most recent first.
    """
    verificar_rol_empleado(token_obj.credentials if token_obj else None, ["ADMIN", "GERENTE", "INVENTARIO"], session)

    ing = session.get(Ingrediente, ingrediente_id)
    if not ing:
        raise HTTPException(status_code=404, detail="Ingrediente no encontrado.")

    stmt = (
        select(MovimientoIngrediente)
        .where(col(MovimientoIngrediente.ingrediente_id) == ingrediente_id)
        .order_by(col(MovimientoIngrediente.id).desc())
        .limit(limite)
    )
    if tipo:
        stmt = stmt.where(col(MovimientoIngrediente.tipo_movimiento) == tipo.upper())

    return session.exec(stmt).all()
