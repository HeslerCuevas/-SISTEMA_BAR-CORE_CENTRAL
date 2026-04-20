from typing import List
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.db.database import get_session
from app.models.core_models import Empleado

router = APIRouter(prefix="/api/v1/empleados", tags=["Gestión de Personal"])


@router.get("/", response_model=List[dict])
async def obtener_todos_los_empleados(db: Session = Depends(get_session)):
    statement = select(Empleado).where(Empleado.activo == True)
    empleados = db.exec(statement).all()

    resultado = []
    for emp in empleados:
        resultado.append({
            "id": emp.id,
            "rol_id": emp.rol_id,
            "sucursal_id": emp.sucursal_id,
            "documento_identidad": emp.documento_identidad,
            "nombre_completo": emp.nombre_completo,
            "email": emp.email,
            "password_hash": emp.password_hash,
            "activo": emp.activo
        })

    return resultado