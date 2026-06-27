from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordRequestForm, HTTPAuthorizationCredentials
from sqlmodel import Session, select
from sqlalchemy import or_
from typing import Optional
from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from app.db.database import get_session
from app.schemas.auth_schema import (
    LoginResponse,
    CambioPasswordEmpleadoRequest,
    CambioPasswordAdminRequest,
    SolicitarResetRequest,
    ConfirmarResetRequest,
    PasswordResetResponse,
)
from app.models.core_models import Empleado, Rol, PasswordResetToken
from app.core.security import (
    verify_password, create_access_token, get_password_hash,
    oauth2_scheme, verificar_rol_empleado, decode_access_token, security_bearer
)
from app.services.audit_service import log_auditoria
from app.services.email_service import enviar_email_reset_password

router = APIRouter(prefix="/api/v1/auth", tags=["Seguridad"])

TOKEN_RESET_EXPIRACION_MINUTOS = 30


# ─── Login ─────────────────────────────────────────────────────────────────────

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
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    if not empleado.activo:
        raise HTTPException(
            status_code=403,
            detail="El usuario está inactivo en el sistema central."
        )

    rol = session.get(Rol, empleado.rol_id)
    access_token = create_access_token(subject=str(empleado.id), canal="CORE_WEB")

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "empleado_id": empleado.id,
        "nombre": empleado.nombre_completo,
        "rol": rol.nombre if rol else "Sin Rol",
        "sucursal_id": empleado.sucursal_id,
        "activo": empleado.activo
    }


# ─── Cambio de contraseña propia ──────────────────────────────────────────────

@router.post("/cambiar-password", response_model=PasswordResetResponse)
def cambiar_password_empleado(
    payload: CambioPasswordEmpleadoRequest,
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    """El empleado cambia su propia contraseña validando la actual."""
    if not token_obj:
        raise HTTPException(status_code=401, detail="Se requiere autenticación.")

    t = decode_access_token(token_obj.credentials)
    if not t:
        raise HTTPException(status_code=401, detail="Token inválido o expirado.")

    empleado = session.get(Empleado, int(t["sub"]))
    if not empleado or not empleado.activo:
        raise HTTPException(status_code=404, detail="Empleado no encontrado o inactivo.")

    if not verify_password(payload.password_actual, empleado.password_hash):
        raise HTTPException(status_code=400, detail="La contraseña actual es incorrecta.")

    empleado.password_hash = get_password_hash(payload.password_nuevo)
    session.add(empleado)
    session.commit()

    log_auditoria(
        nivel="INFO",
        origen="POST /api/v1/auth/cambiar-password",
        mensaje=f"Empleado id={empleado.id} cambió su contraseña exitosamente.",
    )
    return PasswordResetResponse(mensaje="Contraseña actualizada exitosamente.")


# ─── Cambio de contraseña por administrador ───────────────────────────────────

@router.post("/empleados/{empleado_id}/cambiar-password-admin", response_model=PasswordResetResponse)
def cambiar_password_admin(
    empleado_id: int,
    payload: CambioPasswordAdminRequest,
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    """Un ADMIN cambia la contraseña de cualquier empleado sin requerir la actual."""
    info = verificar_rol_empleado(token_obj.credentials if token_obj else None, ["ADMIN"], session)

    empleado = session.get(Empleado, empleado_id)
    if not empleado:
        raise HTTPException(status_code=404, detail="Empleado no encontrado.")

    empleado.password_hash = get_password_hash(payload.nuevo_password)
    session.add(empleado)
    session.commit()

    log_auditoria(
        nivel="WARNING",
        origen=f"POST /api/v1/auth/empleados/{empleado_id}/cambiar-password-admin",
        mensaje=f"Admin id={info['empleado_id']} cambió la contraseña del empleado id={empleado_id}.",
        data={"admin_id": info["empleado_id"], "objetivo_id": empleado_id}
    )
    return PasswordResetResponse(
        mensaje=f"Contraseña del empleado '{empleado.nombre_completo}' actualizada por el administrador."
    )


# ─── Solicitar reset de contraseña ────────────────────────────────────────────

@router.post("/solicitar-reset", response_model=PasswordResetResponse)
def solicitar_reset_password_empleado(
    payload: SolicitarResetRequest,
    session: Session = Depends(get_session)
):
    """Genera un token de reset y lo envía por email al empleado."""
    empleado = session.exec(select(Empleado).where(Empleado.email == payload.email)).first()

    # Respuesta genérica para no revelar si el email existe
    respuesta_generica = PasswordResetResponse(
        mensaje="If the email is registered, you will receive a recovery link shortly."
    )

    if not empleado or not empleado.activo:
        return respuesta_generica

    # Invalidar tokens anteriores no usados para este empleado
    tokens_anteriores = session.exec(
        select(PasswordResetToken).where(
            PasswordResetToken.entidad_tipo == "EMPLEADO",
            PasswordResetToken.entidad_id == empleado.id,
            PasswordResetToken.usado == False,
        )
    ).all()
    for t in tokens_anteriores:
        t.usado = True
        session.add(t)

    # Generar token único
    token_plano = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token_plano.encode()).hexdigest()
    expira_en = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=TOKEN_RESET_EXPIRACION_MINUTOS)

    reset_token = PasswordResetToken(
        token_hash=token_hash,
        entidad_tipo="EMPLEADO",
        entidad_id=empleado.id,
        expira_en=expira_en,
        usado=False,
    )
    session.add(reset_token)
    session.commit()

    log_auditoria(
        nivel="INFO",
        origen="POST /api/v1/auth/solicitar-reset",
        mensaje=f"Reset de contraseña solicitado para empleado id={empleado.id}, email={empleado.email}",
    )

    enviar_email_reset_password(empleado.email, token_plano, tipo="empleado")
    return respuesta_generica


# ─── Confirmar reset de contraseña ────────────────────────────────────────────

@router.post("/confirmar-reset", response_model=PasswordResetResponse)
def confirmar_reset_password_empleado(
    payload: ConfirmarResetRequest,
    session: Session = Depends(get_session)
):
    """Valida el token de reset y establece la nueva contraseña."""
    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    ahora = datetime.now(timezone.utc).replace(tzinfo=None)

    reset_token = session.exec(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.entidad_tipo == "EMPLEADO",
            PasswordResetToken.usado == False,
        )
    ).first()

    if not reset_token:
        raise HTTPException(status_code=400, detail="Token de recuperación inválido o ya utilizado.")

    if reset_token.expira_en < ahora:
        reset_token.usado = True
        session.add(reset_token)
        session.commit()
        raise HTTPException(status_code=400, detail="El token de recuperación ha expirado. Solicita uno nuevo.")

    empleado = session.get(Empleado, reset_token.entidad_id)
    if not empleado or not empleado.activo:
        raise HTTPException(status_code=404, detail="Empleado no encontrado o inactivo.")

    empleado.password_hash = get_password_hash(payload.password_nuevo)
    reset_token.usado = True

    session.add(empleado)
    session.add(reset_token)
    session.commit()

    log_auditoria(
        nivel="INFO",
        origen="POST /api/v1/auth/confirmar-reset",
        mensaje=f"Contraseña restablecida exitosamente para empleado id={empleado.id}.",
    )
    return PasswordResetResponse(mensaje="Contraseña restablecida exitosamente. Ya puedes iniciar sesión.")