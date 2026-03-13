from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db.database import get_session
from app.models.core_models import InventarioActual, MovimientoInventario, Producto
from app.schemas.inventario_schema import MovimientoCreate, InventarioResponse

router = APIRouter(
    prefix="/api/v1/inventario",
    tags=["Módulo de Inventario (Kardex)"]
)


@router.post("/movimiento", status_code=201)
def registrar_movimiento(mov_in: MovimientoCreate, session: Session = Depends(get_session)):
    if mov_in.tipo_movimiento not in ["ENTRADA", "SALIDA", "AJUSTE"]:
        raise HTTPException(status_code=400, detail="Tipo de movimiento inválido.")

    inventario_db = session.exec(
        select(InventarioActual).where(InventarioActual.producto_id == mov_in.producto_id)
    ).first()

    if not inventario_db:
        raise HTTPException(status_code=404, detail="El producto no tiene registro de inventario.")

    try:
        if mov_in.tipo_movimiento == "ENTRADA":
            inventario_db.cantidad_disponible += mov_in.cantidad
        elif mov_in.tipo_movimiento in ["SALIDA", "AJUSTE"]:
            if inventario_db.cantidad_disponible < mov_in.cantidad:
                raise HTTPException(status_code=400, detail="Stock insuficiente para esta salida.")
            inventario_db.cantidad_disponible -= mov_in.cantidad

        session.add(inventario_db)

        nuevo_movimiento = MovimientoInventario(**mov_in.model_dump())
        session.add(nuevo_movimiento)

        session.commit()
        return {"mensaje": "Movimiento registrado con éxito", "nuevo_stock": inventario_db.cantidad_disponible}

    except HTTPException:
        raise
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