from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from app.db.database import get_session
from app.models.core_models import Empleado, Rol
from app.schemas.auth_schema import LoginResponse

router = APIRouter(prefix="/auth", tags=["Seguridad"])

@router.post("/login", response_model=LoginResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    statement = select(Empleado).where(Empleado.email == form_data.username)
    empleado = session.exec(statement).first()

    if not empleado or form_data.password != empleado.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos"
        )

    rol = session.get(Rol, empleado.rol_id)

    return {
        "access_token": empleado.email,
        "token_type": "bearer",
        "nombre": empleado.nombre_completo,
        "rol": rol.nombre if rol else "Sin Rol",
        "sucursal_id": empleado.sucursal_id,
        "empleado_id": empleado.id
    }