from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlmodel import Session, select
from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib
import secrets

from app.db.database import get_session
from app.models.core_models import PasswordResetToken, EmailChangeToken, AccountActionToken
from app.core.timezone import get_local_now
from app.core.security import decode_access_token, security_bearer
from app.services.audit_service import log_auditoria
from app.services.email_service import (
    enviar_email_reset_password,
    enviar_email_cambio_password_notificacion,
    enviar_email_confirmacion_cambio_email_viejo,
    enviar_email_verificacion_nuevo_email,
    enviar_email_solicitud_eliminacion,
    enviar_email_reactivacion,
)
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
    ActualizarPerfilRequest,
    ActualizarPerfilResponse,
    SolicitarCambioEmailRequest,
    SolicitarEliminacionRequest,
    SolicitarReactivacionRequest,
)

router = APIRouter(prefix="/api/v1/clientes/auth", tags=["Seguridad - Clientes Móvil"])

TOKEN_RESET_EXPIRACION_MINUTOS = 30
TOKEN_EMAIL_CHANGE_HORAS    = 24
TOKEN_ACCOUNT_ACTION_HORAS  = 48
TOKEN_PW_RECOVERY_HORAS     = 24


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
            # Distinguishable key so Integration / Flutter can trigger the reactivation flow
            detail="CUENTA_INACTIVA: Esta cuenta ha sido desactivada. Solicita la reactivación desde la app."
        )

    access_token = create_access_token(subject=str(cliente.id), canal="MOVIL")

    return ClienteLoginResponse(
        access_token=access_token,
        token_type="bearer",
        canal="MOVIL",
        cliente_id=cliente.id,
        nombre_completo=cliente.nombre_completo
    )


@router.post("/cambiar-password", response_model=PasswordResetResponse)
def cambiar_password_cliente(
    payload: CambioPasswordClienteRequest,
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    """Authenticated password change. Sends a notification email with a 'wasn't me' recovery link."""
    if not token_obj:
        raise HTTPException(status_code=401, detail="Token de autenticación requerido.")

    t = decode_access_token(token_obj.credentials)
    if not t:
        raise HTTPException(status_code=401, detail="Token inválido o expirado.")

    cliente = session.get(Cliente, int(t["sub"]))
    if not cliente or not cliente.activo:
        raise HTTPException(status_code=404, detail="Cliente no encontrado o inactivo.")

    if not verify_password(payload.password_actual, cliente.password_hash):
        raise HTTPException(status_code=400, detail="La contraseña actual es incorrecta.")

    cliente.password_hash = get_password_hash(payload.password_nuevo)
    session.add(cliente)

    # ── Generate 'wasn't me' recovery token ───────────────────────────────────
    recovery_plano = secrets.token_urlsafe(32)
    recovery_hash  = hashlib.sha256(recovery_plano.encode()).hexdigest()
    recovery_token = AccountActionToken(
        token_hash=recovery_hash,
        entidad_tipo="CLIENTE",
        entidad_id=cliente.id,
        accion="PW_CHANGE_RECOVERY",
        expira_en=get_local_now() + timedelta(hours=TOKEN_PW_RECOVERY_HORAS),
        usado=False,
    )
    session.add(recovery_token)
    session.commit()

    log_auditoria(
        nivel="INFO",
        origen="POST /api/v1/clientes/auth/cambiar-password",
        mensaje=f"Cliente id={cliente.id} cambió su contraseña exitosamente.",
    )

    # Send notification (non-blocking: if email fails it raises but password is already saved)
    enviar_email_cambio_password_notificacion(cliente.email, recovery_plano)

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
        mensaje="If the email is registered, you will receive a recovery link shortly."
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
    expira_en = get_local_now() + timedelta(minutes=TOKEN_RESET_EXPIRACION_MINUTOS)

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
    ahora = get_local_now()

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


# ─── Actualizar perfil (nombre) ────────────────────────────────────────────────

@router.put("/perfil", response_model=ActualizarPerfilResponse)
def actualizar_perfil_cliente(
    payload: ActualizarPerfilRequest,
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    """Updates the authenticated client's display name."""
    if not token_obj:
        raise HTTPException(status_code=401, detail="Token de autenticación requerido.")

    t = decode_access_token(token_obj.credentials)
    if not t:
        raise HTTPException(status_code=401, detail="Token inválido o expirado.")

    cliente = session.get(Cliente, int(t["sub"]))
    if not cliente or not cliente.activo:
        raise HTTPException(status_code=404, detail="Cliente no encontrado o inactivo.")

    cliente.nombre_completo = payload.nombre_completo
    session.add(cliente)
    session.commit()
    session.refresh(cliente)

    log_auditoria(
        nivel="INFO",
        origen="PUT /api/v1/clientes/auth/perfil",
        mensaje=f"Cliente id={cliente.id} actualizó su nombre.",
    )
    return ActualizarPerfilResponse(
        mensaje="Perfil actualizado exitosamente.",
        nombre_completo=cliente.nombre_completo,
    )


# ─── Solicitar cambio de email ─────────────────────────────────────────────────

@router.post("/solicitar-cambio-email", response_model=PasswordResetResponse)
def solicitar_cambio_email(
    payload: SolicitarCambioEmailRequest,
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    """
    Initiates the dual-confirmation email change flow.
    Sends:
      1. Authorization email to the CURRENT address (tipo=OLD_CONFIRM)
      2. Verification email to the NEW address  (tipo=NEW_CONFIRM)
    The email is only updated after BOTH links have been clicked.
    """
    if not token_obj:
        raise HTTPException(status_code=401, detail="Token de autenticación requerido.")

    t = decode_access_token(token_obj.credentials)
    if not t:
        raise HTTPException(status_code=401, detail="Token inválido o expirado.")

    cliente = session.get(Cliente, int(t["sub"]))
    if not cliente or not cliente.activo:
        raise HTTPException(status_code=404, detail="Cliente no encontrado o inactivo.")

    if not verify_password(payload.password_actual, cliente.password_hash):
        raise HTTPException(status_code=400, detail="La contraseña actual es incorrecta.")

    nuevo_email = payload.nuevo_email.strip().lower()

    if nuevo_email == cliente.email.strip().lower():
        raise HTTPException(status_code=400, detail="El nuevo email es idéntico al email actual.")

    # Check if new email already belongs to another account
    ya_existe = session.exec(select(Cliente).where(Cliente.email == nuevo_email)).first()
    if ya_existe:
        raise HTTPException(status_code=400, detail="Este correo electrónico ya está registrado en otra cuenta.")

    expira_en = get_local_now() + timedelta(hours=TOKEN_EMAIL_CHANGE_HORAS)

    # Invalidate previous pending email-change tokens for this client
    tokens_anteriores = session.exec(
        select(EmailChangeToken).where(
            EmailChangeToken.entidad_id == cliente.id,
            EmailChangeToken.usado == False,
        )
    ).all()
    for tk in tokens_anteriores:
        tk.usado = True
        session.add(tk)

    # OLD_CONFIRM — sent to current email
    token_old_plano = secrets.token_urlsafe(32)
    token_old_hash  = hashlib.sha256(token_old_plano.encode()).hexdigest()
    session.add(EmailChangeToken(
        token_hash=token_old_hash,
        entidad_id=cliente.id,
        nuevo_email=nuevo_email,
        tipo="OLD_CONFIRM",
        expira_en=expira_en,
        usado=False,
    ))

    # NEW_CONFIRM — sent to the new email
    token_new_plano = secrets.token_urlsafe(32)
    token_new_hash  = hashlib.sha256(token_new_plano.encode()).hexdigest()
    session.add(EmailChangeToken(
        token_hash=token_new_hash,
        entidad_id=cliente.id,
        nuevo_email=nuevo_email,
        tipo="NEW_CONFIRM",
        expira_en=expira_en,
        usado=False,
    ))
    session.commit()

    enviar_email_confirmacion_cambio_email_viejo(cliente.email, nuevo_email, token_old_plano)
    enviar_email_verificacion_nuevo_email(nuevo_email, token_new_plano)

    log_auditoria(
        nivel="INFO",
        origen="POST /api/v1/clientes/auth/solicitar-cambio-email",
        mensaje=f"Cliente id={cliente.id} solicitó cambio de email a {nuevo_email}.",
    )
    return PasswordResetResponse(
        mensaje="Se han enviado correos de confirmación a tu email actual y al nuevo. "
                "El cambio se aplicará cuando ambos sean confirmados."
    )


# ─── Confirmar cambio de email ─────────────────────────────────────────────────

@router.get("/confirmar-cambio-email", response_model=PasswordResetResponse)
def confirmar_cambio_email(
    token: str,
    tipo: str,
    session: Session = Depends(get_session)
):
    """
    Confirms one side of the email-change flow.
    tipo: 'old' (authorization from current email) | 'new' (verification from new email)
    The email is applied only after both sides are confirmed.
    """
    tipo_db = "OLD_CONFIRM" if tipo == "old" else "NEW_CONFIRM"
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    ahora = get_local_now()

    email_token = session.exec(
        select(EmailChangeToken).where(
            EmailChangeToken.token_hash == token_hash,
            EmailChangeToken.tipo == tipo_db,
            EmailChangeToken.usado == False,
        )
    ).first()

    if not email_token:
        raise HTTPException(status_code=400, detail="Token de cambio de email inválido o ya utilizado.")

    if email_token.expira_en < ahora:
        email_token.usado = True
        session.add(email_token)
        session.commit()
        raise HTTPException(status_code=400, detail="El enlace ha expirado. Solicita un nuevo cambio de email desde la app.")

    email_token.usado = True
    session.add(email_token)

    # Check if the OTHER side has already been confirmed
    otro_tipo = "NEW_CONFIRM" if tipo_db == "OLD_CONFIRM" else "OLD_CONFIRM"
    otro_token = session.exec(
        select(EmailChangeToken).where(
            EmailChangeToken.entidad_id == email_token.entidad_id,
            EmailChangeToken.nuevo_email == email_token.nuevo_email,
            EmailChangeToken.tipo == otro_tipo,
            EmailChangeToken.usado == True,
        )
    ).first()

    if otro_token:
        # Both sides confirmed — apply the email change
        cliente = session.get(Cliente, email_token.entidad_id)
        if not cliente or not cliente.activo:
            raise HTTPException(status_code=404, detail="Cliente no encontrado o inactivo.")

        cliente.email = email_token.nuevo_email
        session.add(cliente)
        session.commit()

        log_auditoria(
            nivel="INFO",
            origen="GET /api/v1/clientes/auth/confirmar-cambio-email",
            mensaje=f"Email de cliente id={cliente.id} actualizado a {cliente.email}.",
        )
        return PasswordResetResponse(mensaje="¡Email actualizado exitosamente! Ya puedes iniciar sesión con tu nuevo email.")
    else:
        session.commit()
        return PasswordResetResponse(
            mensaje="Confirmación recibida. El email se actualizará cuando la otra parte también confirme."
        )


# ─── Solicitar eliminación de cuenta ──────────────────────────────────────────

@router.post("/solicitar-eliminacion", response_model=PasswordResetResponse)
def solicitar_eliminacion_cuenta(
    payload: SolicitarEliminacionRequest,
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    """Sends a deletion-confirmation email. The account is only deactivated after the link is clicked."""
    if not token_obj:
        raise HTTPException(status_code=401, detail="Token de autenticación requerido.")

    t = decode_access_token(token_obj.credentials)
    if not t:
        raise HTTPException(status_code=401, detail="Token inválido o expirado.")

    cliente = session.get(Cliente, int(t["sub"]))
    if not cliente or not cliente.activo:
        raise HTTPException(status_code=404, detail="Cliente no encontrado o inactivo.")

    if not verify_password(payload.password_actual, cliente.password_hash):
        raise HTTPException(status_code=400, detail="La contraseña es incorrecta.")

    token_plano = secrets.token_urlsafe(32)
    token_hash  = hashlib.sha256(token_plano.encode()).hexdigest()
    session.add(AccountActionToken(
        token_hash=token_hash,
        entidad_tipo="CLIENTE",
        entidad_id=cliente.id,
        accion="DELETE",
        expira_en=get_local_now() + timedelta(hours=TOKEN_ACCOUNT_ACTION_HORAS),
        usado=False,
    ))
    session.commit()

    enviar_email_solicitud_eliminacion(cliente.email, token_plano)

    log_auditoria(
        nivel="INFO",
        origen="POST /api/v1/clientes/auth/solicitar-eliminacion",
        mensaje=f"Cliente id={cliente.id} solicitó eliminación de cuenta.",
    )
    return PasswordResetResponse(
        mensaje="Se ha enviado un correo de confirmación. Tu cuenta se desactivará solo si confirmas desde el enlace."
    )


# ─── Confirmar eliminación de cuenta ──────────────────────────────────────────

@router.get("/confirmar-eliminacion", response_model=PasswordResetResponse)
def confirmar_eliminacion_cuenta(
    token: str,
    session: Session = Depends(get_session)
):
    """Soft-deletes the account by setting activo=False. Records are never permanently removed."""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    ahora = get_local_now()

    action_token = session.exec(
        select(AccountActionToken).where(
            AccountActionToken.token_hash == token_hash,
            AccountActionToken.accion == "DELETE",
            AccountActionToken.entidad_tipo == "CLIENTE",
            AccountActionToken.usado == False,
        )
    ).first()

    if not action_token:
        raise HTTPException(status_code=400, detail="Enlace de eliminación inválido o ya utilizado.")

    if action_token.expira_en < ahora:
        action_token.usado = True
        session.add(action_token)
        session.commit()
        raise HTTPException(status_code=400, detail="El enlace de eliminación ha expirado. Solicita uno nuevo desde la app.")

    cliente = session.get(Cliente, action_token.entidad_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")

    cliente.activo = False
    action_token.usado = True
    session.add(cliente)
    session.add(action_token)
    session.commit()

    log_auditoria(
        nivel="INFO",
        origen="GET /api/v1/clientes/auth/confirmar-eliminacion",
        mensaje=f"Cuenta de cliente id={cliente.id} desactivada (soft-delete).",
    )
    return PasswordResetResponse(mensaje="Tu cuenta ha sido desactivada. Si cambias de opinión, puedes reactivarla desde la app.")


# ─── Solicitar reactivación de cuenta ─────────────────────────────────────────

@router.post("/reactivar", response_model=PasswordResetResponse)
def solicitar_reactivacion_cuenta(
    payload: SolicitarReactivacionRequest,
    session: Session = Depends(get_session)
):
    """Sends a reactivation link to the email if an inactive account exists for it."""
    # Generic response to avoid email enumeration
    respuesta_generica = PasswordResetResponse(
        mensaje="If an inactive account exists for this email, a reactivation link has been sent."
    )

    cliente = session.exec(select(Cliente).where(Cliente.email == payload.email.strip().lower())).first()
    if not cliente or cliente.activo:
        return respuesta_generica

    token_plano = secrets.token_urlsafe(32)
    token_hash  = hashlib.sha256(token_plano.encode()).hexdigest()
    session.add(AccountActionToken(
        token_hash=token_hash,
        entidad_tipo="CLIENTE",
        entidad_id=cliente.id,
        accion="REACTIVATE",
        expira_en=get_local_now() + timedelta(hours=TOKEN_ACCOUNT_ACTION_HORAS),
        usado=False,
    ))
    session.commit()

    enviar_email_reactivacion(cliente.email, token_plano)

    log_auditoria(
        nivel="INFO",
        origen="POST /api/v1/clientes/auth/reactivar",
        mensaje=f"Reactivación solicitada para cliente id={cliente.id}.",
    )
    return respuesta_generica


# ─── Confirmar reactivación de cuenta ─────────────────────────────────────────

@router.get("/confirmar-reactivacion", response_model=PasswordResetResponse)
def confirmar_reactivacion_cuenta(
    token: str,
    session: Session = Depends(get_session)
):
    """Reactivates the account by setting activo=True after validating the token."""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    ahora = get_local_now()

    action_token = session.exec(
        select(AccountActionToken).where(
            AccountActionToken.token_hash == token_hash,
            AccountActionToken.accion == "REACTIVATE",
            AccountActionToken.entidad_tipo == "CLIENTE",
            AccountActionToken.usado == False,
        )
    ).first()

    if not action_token:
        raise HTTPException(status_code=400, detail="Enlace de reactivación inválido o ya utilizado.")

    if action_token.expira_en < ahora:
        action_token.usado = True
        session.add(action_token)
        session.commit()
        raise HTTPException(status_code=400, detail="El enlace de reactivación ha expirado. Solicita uno nuevo desde la app.")

    cliente = session.get(Cliente, action_token.entidad_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")

    cliente.activo = True
    action_token.usado = True
    session.add(cliente)
    session.add(action_token)
    session.commit()

    log_auditoria(
        nivel="INFO",
        origen="GET /api/v1/clientes/auth/confirmar-reactivacion",
        mensaje=f"Cuenta de cliente id={cliente.id} reactivada exitosamente.",
    )
    return PasswordResetResponse(mensaje="¡Tu cuenta ha sido reactivada exitosamente! Ya puedes iniciar sesión.")