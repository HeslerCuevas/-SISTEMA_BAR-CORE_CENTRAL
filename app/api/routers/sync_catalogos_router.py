from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
from datetime import datetime
from typing import List
from app.db.database import get_session
from app.models.core_models import Producto, InventarioActual
from app.schemas.producto_schema import ProductoResponse
from app.schemas.inventario_schema import InventarioResponse

router = APIRouter(prefix="/api/v1/sync/catalogos", tags=["Sincronización de Catálogo"])

@router.get("/productos", response_model=List[ProductoResponse])
def sync_productos(
    last_sync: datetime = Query(..., description="Fecha de la última sincronización de la caja"),
    session: Session = Depends(get_session)
):
    statement = select(Producto).where(Producto.ultima_modificacion > last_sync)
    return session.exec(statement).all()

@router.get("/inventario", response_model=List[InventarioResponse])
def sync_inventario(
    last_sync: datetime = Query(..., description="Fecha de la última sincronización de stock"),
    session: Session = Depends(get_session)
):
    statement = select(InventarioActual).where(InventarioActual.ultima_modificacion > last_sync)
    return session.exec(statement).all()