from typing import List
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.db.database import get_session
from app.models.core_models import Rol

router = APIRouter(prefix="/api/v1/roles", tags=["Catálogos"])

@router.get("/", response_model=List[dict])
async def obtener_roles(db: Session = Depends(get_session)):
    statement = select(Rol)
    roles = db.exec(statement).all()
    return [{"id": r.id, "nombre": r.nombre} for r in roles]