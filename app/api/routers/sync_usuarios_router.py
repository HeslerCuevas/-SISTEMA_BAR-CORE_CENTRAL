from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
from datetime import datetime
from typing import List
from app.db.database import get_session
from app.models.core_models import Empleado
from app.schemas.auth_schema import EmpleadoResponse

router = APIRouter(prefix="/api/v1/sync/seguridad", tags=["Sincronización de Seguridad"])


@router.get("/usuarios", response_model=List[EmpleadoResponse])
def sync_usuarios(
        sucursal_id: int = Query(..., description="ID de la sucursal que solicita datos"),
        last_sync: datetime = Query(None, description="Opcional: solo usuarios modificados"),
        session: Session = Depends(get_session)
):
    statement = select(Empleado).where(
        Empleado.sucursal_id == sucursal_id,
        Empleado.activo == True
    )

    if last_sync:
        statement = statement.where(Empleado.ultima_modificacion > last_sync)

    return session.exec(statement).all()