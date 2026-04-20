from typing import List
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.db.database import get_session
from app.models.core_models import Sucursal

router = APIRouter(prefix="/api/v1/sucursales", tags=["Catálogos"])

@router.get("/", response_model=List[dict])
async def obtener_sucursales(db: Session = Depends(get_session)):
    statement = select(Sucursal).where(Sucursal.activo == True)
    sucursales = db.exec(statement).all()
    return [{"id": s.id, "nombre": s.nombre} for s in sucursales]