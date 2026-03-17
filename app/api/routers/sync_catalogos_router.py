from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select, col, or_
from datetime import datetime
from typing import List
from app.db.database import get_session
from app.models.core_models import Producto, InventarioActual, Impuesto
from app.schemas.producto_schema import ProductoResponse

router = APIRouter(prefix="/api/v1/sync", tags=["Sincronización Inteligente"])


@router.get("/delta", response_model=List[ProductoResponse])
def sync_delta(
        last_sync: datetime = Query(..., description="Fecha de la última vez que la caja pidió datos"),
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
        .where(
            or_(
                col(Producto.ultima_modificacion) > last_sync,
                col(InventarioActual.ultima_modificacion) > last_sync
            )
        )
    )

    results = session.exec(statement).all()

    lista_actualizada = []
    for producto, tasa, stock in results:
        p_data = producto.model_dump()
        p_data["tasa_impuesto"] = (tasa / 100) if tasa is not None else 0
        p_data["cantidad_disponible"] = stock if stock is not None else 0
        lista_actualizada.append(p_data)

    return lista_actualizada