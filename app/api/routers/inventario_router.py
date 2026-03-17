from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.db.database import get_session
from app.models.core_models import InventarioActual
from app.schemas.inventario_schema import MovimientoCreate, InventarioResponse

# IMPORTANTE: Importa tu Manager
from app.logic.inventory_manager import InventoryManager

router = APIRouter(
    prefix="/api/v1/inventario",
    tags=["Módulo de Inventario"]
)

@router.post("/movimiento", status_code=201)
def registrar_movimiento(mov_in: MovimientoCreate, session: Session = Depends(get_session)):
    try:
        InventoryManager.registrar_movimiento(
            session=session,
            producto_id=mov_in.producto_id,
            cantidad=mov_in.cantidad,
            tipo=mov_in.tipo_movimiento,
            motivo=mov_in.motivo,
            empleado_id=mov_in.empleado_id
        )

        session.commit()

        stock_actualizado = session.exec(
            select(InventarioActual).where(InventarioActual.producto_id == mov_in.producto_id)
        ).first()

        return {
            "mensaje": "Movimiento registrado con éxito",
            "nuevo_stock": stock_actualizado.cantidad_disponible
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.get("/{producto_id}", response_model=InventarioResponse)
def consultar_stock(producto_id: int, session: Session = Depends(get_session)):
    inventario = session.exec(
        select(InventarioActual).where(InventarioActual.producto_id == producto_id)
    ).first()

    if not inventario:
        raise HTTPException(status_code=404, detail="Inventario no encontrado")

    return inventario