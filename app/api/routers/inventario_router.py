from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials
from sqlmodel import Session, select, col
from app.db.database import get_session
from app.models.core_models import InventarioActual, MovimientoInventario, MovimientoIngrediente, Producto
from app.schemas.inventario_schema import MovimientoCreate, InventarioResponse, MovimientoInventarioResponse
from app.schemas.ingredientes_schema import MovimientoIngredienteResponse
from app.logic.inventory_manager import InventoryManager
from app.logic.ingredient_inventory_manager import IngredientInventoryManager
from app.core.security import security_bearer, verificar_rol_empleado
from app.services.audit_service import log_auditoria

router = APIRouter(
    prefix="/api/v1/inventario",
    tags=["Módulo de Inventario"]
)

from fastapi import Header
import os
from datetime import datetime


@router.post("/movimiento", status_code=201)
def registrar_movimiento(
        mov_in: MovimientoCreate,
        session: Session = Depends(get_session),
        token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
        x_gateway_token: Optional[str] = Header(None)
):
    gateway_secret = os.getenv("CORE_SECRET_KEY")
    is_gateway = x_gateway_token and gateway_secret and x_gateway_token == gateway_secret

    if is_gateway:
        if not mov_in.empleado_id:
            raise HTTPException(status_code=400, detail="empleado_id es obligatorio para sincronización Gateway")
        empleado_id_final = mov_in.empleado_id
    else:
        if not token_obj or not token_obj.credentials:
            raise HTTPException(status_code=401, detail="Token Bearer ausente o inválido")
        empleado_info = verificar_rol_empleado(token_obj.credentials, ["ADMIN", "GERENTE", "INVENTARIO"], session)
        empleado_id_final = empleado_info["empleado_id"]

    try:
        stock_actualizado = InventoryManager.registrar_movimiento(
            session=session,
            producto_id=mov_in.producto_id,
            cantidad=mov_in.cantidad,
            tipo=mov_in.tipo_movimiento,
            motivo=mov_in.motivo,
            empleado_id=empleado_id_final,
            movimiento_local_uuid=mov_in.movimiento_local_uuid
        )

        session.commit()

        log_auditoria(
            nivel="INFO",
            origen="POST /api/v1/inventario/movimiento",
            mensaje=f"Movimiento {mov_in.tipo_movimiento} de {mov_in.cantidad} unidades registrado para producto id={mov_in.producto_id}.",
            data=mov_in.model_dump()
        )

        return {
            "mensaje": "Movimiento registrado con éxito",
            "nuevo_stock": stock_actualizado.cantidad_disponible
        }

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/{producto_id}", response_model=InventarioResponse)
def consultar_stock(
        producto_id: int,
        session: Session = Depends(get_session),
        token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
        x_gateway_token: Optional[str] = Header(None)
):
    gateway_secret = os.getenv("CORE_SECRET_KEY")
    is_gateway = x_gateway_token and gateway_secret and x_gateway_token == gateway_secret

    if not is_gateway:
        if not token_obj or not token_obj.credentials:
            raise HTTPException(status_code=401, detail="Token Bearer ausente o inválido")
        verificar_rol_empleado(token_obj.credentials, [], session)

    producto = session.get(Producto, producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    tipo_control = getattr(producto, "tipo_control_inventario", "PRODUCTO")

    if tipo_control == "NINGUNO":
        return InventarioResponse(
            producto_id=producto_id, cantidad_disponible=9999,
            stock_minimo=0, ultima_actualizacion=datetime.utcnow(),
            ultima_modificacion=datetime.utcnow()
        )

    if tipo_control == "INGREDIENTES":
        disp = IngredientInventoryManager.calcular_disponibilidad_producto(session, producto.id)
        return InventarioResponse(
            producto_id=producto_id, cantidad_disponible=disp.get("cantidad_producible", 0),
            stock_minimo=0, ultima_actualizacion=datetime.utcnow(),
            ultima_modificacion=datetime.utcnow()
        )

    inventario = session.exec(
        select(InventarioActual).where(InventarioActual.producto_id == producto_id)
    ).first()

    if not inventario:
        raise HTTPException(status_code=404, detail="Inventario no encontrado")

    return inventario


@router.get("/productos/{producto_id}/movimientos", response_model=List[MovimientoInventarioResponse])
def listar_movimientos_producto(
        producto_id: int,
        limite: int = Query(50, ge=1, le=500, description="Máximo de registros a retornar"),
        tipo: Optional[str] = Query(None, description="Filtrar por tipo de movimiento"),
        session: Session = Depends(get_session),
        token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    if not token_obj or not token_obj.credentials:
        raise HTTPException(status_code=401, detail="Token Bearer ausente o inválido")

    verificar_rol_empleado(token_obj.credentials, ["ADMIN", "GERENTE", "INVENTARIO"], session)

    stmt = select(MovimientoInventario).where(MovimientoInventario.producto_id == producto_id)
    if tipo:
        stmt = stmt.where(MovimientoInventario.tipo_movimiento == tipo)
    
    stmt = stmt.order_by(col(MovimientoInventario.id).desc()).limit(limite)
    return session.exec(stmt).all()


@router.get("/ingredientes/{ingrediente_id}/movimientos", response_model=List[MovimientoIngredienteResponse])
def listar_movimientos_ingrediente_inventario(
        ingrediente_id: int,
        limite: int = Query(50, ge=1, le=500, description="Máximo de registros a retornar"),
        tipo: Optional[str] = Query(None, description="Filtrar por tipo de movimiento"),
        session: Session = Depends(get_session),
        token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    if not token_obj or not token_obj.credentials:
        raise HTTPException(status_code=401, detail="Token Bearer ausente o inválido")

    verificar_rol_empleado(token_obj.credentials, ["ADMIN", "GERENTE", "INVENTARIO"], session)

    stmt = select(MovimientoIngrediente).where(MovimientoIngrediente.ingrediente_id == ingrediente_id)
    if tipo:
        stmt = stmt.where(MovimientoIngrediente.tipo_movimiento == tipo)
    
    stmt = stmt.order_by(col(MovimientoIngrediente.id).desc()).limit(limite)
    return session.exec(stmt).all()