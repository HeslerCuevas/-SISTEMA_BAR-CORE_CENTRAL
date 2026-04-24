from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from sqlalchemy import or_

from app.db.database import get_session
from app.schemas.auth_schema import LoginResponse
from app.models.core_models import Empleado, Rol
from app.core.security import verify_password, create_access_token

router = APIRouter(prefix="/api/v1/auth", tags=["Seguridad"])

@router.post("/login", response_model=LoginResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    statement = select(Empleado).where(
        or_(
            Empleado.email == form_data.username,
            Empleado.documento_identidad == form_data.username
        )
    )
    empleado = session.exec(statement).first()

    if not empleado or not verify_password(form_data.password, empleado.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas"
        )

    if not empleado.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario está inactivo en el sistema central."
        )

    rol = session.get(Rol, empleado.rol_id)

    access_token = create_access_token(
        subject=str(empleado.id),
        canal="CORE_WEB"
    )


    return {
        "access_token": access_token,
        "token_type": "bearer",
        "empleado_id": empleado.id,
        "nombre": empleado.nombre_completo,
        "rol": rol.nombre if rol else "Sin Rol",
        "sucursal_id": empleado.sucursal_id,
        "activo": empleado.activo
    }