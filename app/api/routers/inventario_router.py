from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlmodel import Session, select
from app.db.database import get_session
from app.models.core_models import InventarioActual
from app.schemas.inventario_schema import MovimientoCreate, InventarioResponse
from app.logic.inventory_manager import InventoryManager
from app.core.security import security_bearer, verificar_rol_empleado
from app.services.audit_service import log_auditoria

router = APIRouter(
    prefix="/api/v1/inventario",
    tags=["Módulo de Inventario"]
)


@router.post("/movimiento", status_code=201)
def registrar_movimiento(
        mov_in: MovimientoCreate,
        session: Session = Depends(get_session),
        token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    if not token_obj or not token_obj.credentials:
        raise HTTPException(status_code=401, detail="Token Bearer ausente o inválido")

    empleado_info = verificar_rol_empleado(token_obj.credentials, ["ADMIN", "GERENTE", "INVENTARIO"], session)

    try:
        stock_actualizado = InventoryManager.registrar_movimiento(
            session=session,
            producto_id=mov_in.producto_id,
            cantidad=mov_in.cantidad,
            tipo=mov_in.tipo_movimiento,
            motivo=mov_in.motivo,
            empleado_id=empleado_info["empleado_id"],
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
        token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    if not token_obj or not token_obj.credentials:
        raise HTTPException(status_code=401, detail="Token Bearer ausente o inválido")

    verificar_rol_empleado(token_obj.credentials, [], session)

    inventario = session.exec(
        select(InventarioActual).where(InventarioActual.producto_id == producto_id)
    ).first()

    if not inventario:
        raise HTTPException(status_code=404, detail="Inventario no encontrado")

    return inventario