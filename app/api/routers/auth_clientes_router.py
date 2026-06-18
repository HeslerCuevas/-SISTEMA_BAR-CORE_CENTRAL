from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib
import secrets

from app.db.database import get_session
from app.models.core_models import PasswordResetToken
from app.core.security import oauth2_scheme, decode_access_token
from app.services.audit_service import log_auditoria
from app.services.email_service import enviar_email_reset_password
from app.models.core_models import Cliente
from app.core.security import verify_password, get_password_hash, create_access_token

from app.schemas.auth_schema import (
    ClienteRegistroRequest,
    ClienteRegistroResponse,
    ClienteLoginRequest,
    ClienteLoginResponse,
    CambioPasswordClienteRequest,
    SolicitarResetRequest,
    ConfirmarResetRequest,
    PasswordResetResponse,
)

router = APIRouter(prefix="/api/v1/clientes/auth", tags=["Seguridad - Clientes Móvil"])

TOKEN_RESET_EXPIRACION_MINUTOS = 30


# ─── Registro ──────────────────────────────────────────────────────────────────

@router.post("/registro", response_model=ClienteRegistroResponse, status_code=201)
def registrar_cliente(
    request: ClienteRegistroRequest,
    session: Session = Depends(get_session)
):
    existente = session.exec(select(Cliente).where(Cliente.email == request.email)).first()
    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este correo electrónico ya está registrado."
        )

    hashed_password = get_password_hash(request.password_plano)
    nuevo_cliente = Cliente(
        nombre_completo=request.nombre_completo,
        email=request.email,
        telefono=request.telefono,
        password_hash=hashed_password,
        fecha_registro=datetime.utcnow(),
        activo=True
    )
    session.add(nuevo_cliente)
    session.commit()
    session.refresh(nuevo_cliente)

    return ClienteRegistroResponse(
        mensaje="Cuenta de cliente creada exitosamente.",
        cliente_id=nuevo_cliente.id,
        email=nuevo_cliente.email
    )


# ─── Login ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=ClienteLoginResponse)
def login_cliente(
    request: ClienteLoginRequest,
    session: Session = Depends(get_session)
):
    cliente = session.exec(select(Cliente).where(Cliente.email == request.email)).first()

    if not cliente or not verify_password(request.password_plano, cliente.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos"
        )

    if not cliente.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta cuenta ha sido desactivada."
        )

    access_token = create_access_token(subject=str(cliente.id), canal="MOVIL")

    return ClienteLoginResponse(
        access_token=access_token,
        token_type="bearer",
        canal="MOVIL",
        cliente_id=cliente.id,
        nombre_completo=cliente.nombre_completo
    )


# ─── Cambio de contraseña autenticado ─────────────────────────────────────────

@router.post("/cambiar-password", response_model=PasswordResetResponse)
def cambiar_password_cliente(
    payload: CambioPasswordClienteRequest,
    session: Session = Depends(get_session),
    token: Optional[str] = Depends(oauth2_scheme)
):
    """El cliente cambia su propia contraseña, requiere la actual."""
    if not token:
        raise HTTPException(status_code=401, detail="Se requiere autenticación.")

    t = decode_access_token(token)
    if not t:
        raise HTTPException(status_code=401, detail="Token inválido o expirado.")

    cliente = session.get(Cliente, int(t["sub"]))
    if not cliente or not cliente.activo:
        raise HTTPException(status_code=404, detail="Cliente no encontrado o inactivo.")

    if not verify_password(payload.password_actual, cliente.password_hash):
        raise HTTPException(status_code=400, detail="La contraseña actual es incorrecta.")

    cliente.password_hash = get_password_hash(payload.password_nuevo)
    session.add(cliente)
    session.commit()

    log_auditoria(
        nivel="INFO",
        origen="POST /api/v1/clientes/auth/cambiar-password",
        mensaje=f"Cliente id={cliente.id} cambió su contraseña exitosamente.",
    )
    return PasswordResetResponse(mensaje="Contraseña actualizada exitosamente.")


# ─── Solicitar reset de contraseña ────────────────────────────────────────────

@router.post("/solicitar-reset", response_model=PasswordResetResponse)
def solicitar_reset_cliente(
    payload: SolicitarResetRequest,
    session: Session = Depends(get_session)
):
    """Genera token de reset y lo envía por email al cliente."""
    cliente = session.exec(select(Cliente).where(Cliente.email == payload.email)).first()

    respuesta_generica = PasswordResetResponse(
        mensaje="Si el email está registrado, recibirás un enlace de recuperación en breve."
    )

    if not cliente or not cliente.activo:
        return respuesta_generica

    # Invalidar tokens anteriores
    tokens_anteriores = session.exec(
        select(PasswordResetToken).where(
            PasswordResetToken.entidad_tipo == "CLIENTE",
            PasswordResetToken.entidad_id == cliente.id,
            PasswordResetToken.usado == False,
        )
    ).all()
    for t in tokens_anteriores:
        t.usado = True
        session.add(t)

    token_plano = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token_plano.encode()).hexdigest()
    expira_en = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=TOKEN_RESET_EXPIRACION_MINUTOS)

    reset_token = PasswordResetToken(
        token_hash=token_hash,
        entidad_tipo="CLIENTE",
        entidad_id=cliente.id,
        expira_en=expira_en,
        usado=False,
    )
    session.add(reset_token)
    session.commit()

    log_auditoria(
        nivel="INFO",
        origen="POST /api/v1/clientes/auth/solicitar-reset",
        mensaje=f"Reset solicitado para cliente id={cliente.id}, email={cliente.email}",
    )

    enviar_email_reset_password(cliente.email, token_plano, tipo="cliente")
    return respuesta_generica


# ─── Confirmar reset ───────────────────────────────────────────────────────────

@router.post("/confirmar-reset", response_model=PasswordResetResponse)
def confirmar_reset_cliente(
    payload: ConfirmarResetRequest,
    session: Session = Depends(get_session)
):
    """Valida el token y restablece la contraseña del cliente."""
    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    ahora = datetime.now(timezone.utc).replace(tzinfo=None)

    reset_token = session.exec(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.entidad_tipo == "CLIENTE",
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

    cliente = session.get(Cliente, reset_token.entidad_id)
    if not cliente or not cliente.activo:
        raise HTTPException(status_code=404, detail="Cliente no encontrado o inactivo.")

    cliente.password_hash = get_password_hash(payload.password_nuevo)
    reset_token.usado = True

    session.add(cliente)
    session.add(reset_token)
    session.commit()

    log_auditoria(
        nivel="INFO",
        origen="POST /api/v1/clientes/auth/confirmar-reset",
        mensaje=f"Contraseña restablecida para cliente id={cliente.id}.",
    )
    return PasswordResetResponse(mensaje="Contraseña restablecida exitosamente. Ya puedes iniciar sesión.")