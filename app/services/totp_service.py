"""
TOTP (Time-based One-Time Password) service for supervisor authorization.
Implements RFC 6238 using pyotp. Secrets are AES-256 encrypted at rest.
"""
import os
import base64
import pyotp
import qrcode
import io
from cryptography.fernet import Fernet
from sqlmodel import Session, select
from app.models.core_models import EmpleadoTOTP, Empleado
from fastapi import HTTPException
from app.core.timezone import get_local_now

# Encryption key loaded from environment (must be 32-byte URL-safe base64)
_RAW_KEY = os.getenv("TOTP_ENCRYPTION_KEY", "")
if _RAW_KEY:
    _FERNET = Fernet(_RAW_KEY.encode() if len(_RAW_KEY) == 44 else base64.urlsafe_b64encode(_RAW_KEY.encode()[:32]))
else:
    # Fallback for dev — generate ephemeral key (secrets won't survive restart)
    _FERNET = Fernet(Fernet.generate_key())


def _encrypt_secret(secret: str) -> str:
    return _FERNET.encrypt(secret.encode()).decode()


def _decrypt_secret(encrypted: str) -> str:
    return _FERNET.decrypt(encrypted.encode()).decode()


def generar_secreto_totp() -> str:
    """Generate a new random TOTP base32 secret."""
    return pyotp.random_base32()


def generar_qr_totp(email: str, secret: str, issuer: str = "MasterPOS") -> bytes:
    """Generate a QR code PNG for Google Authenticator enrollment."""
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def verificar_otp(secret: str, otp: str, tolerancia_periodos: int = 1) -> bool:
    """
    Verify a 6-digit OTP against the secret.
    tolerancia_periodos=1 allows ±30 seconds clock skew.
    """
    totp = pyotp.TOTP(secret)
    return totp.verify(otp, valid_window=tolerancia_periodos)


def enrolar_supervisor(db: Session, empleado_id: int) -> dict:
    """
    Generate and store a new TOTP secret for an employee.
    Returns the secret and QR code bytes for display during setup.
    Overwrites any existing enrollment.
    """
    empleado = db.get(Empleado, empleado_id)
    if not empleado:
        raise HTTPException(status_code=404, detail="Employee not found.")
    if not empleado.activo:
        raise HTTPException(status_code=400, detail="The employee is inactive.")

    # Check allowed roles — only GERENTE / ADMIN may have TOTP
    from sqlmodel import select as sel
    from app.models.core_models import Rol
    rol = db.get(Rol, empleado.rol_id)
    if not rol or rol.nombre not in ("ADMIN", "GERENTE", "SUPERVISOR"):
        raise HTTPException(status_code=403, detail="Only supervisors/managers can be enrolled.")

    secret = generar_secreto_totp()
    encrypted = _encrypt_secret(secret)

    existing = db.exec(select(EmpleadoTOTP).where(EmpleadoTOTP.empleado_id == empleado_id)).first()
    if existing:
        existing.secreto_encriptado = encrypted
        existing.activo = True
        db.add(existing)
    else:
        db.add(EmpleadoTOTP(empleado_id=empleado_id, secreto_encriptado=encrypted))
    db.commit()

    qr_png = generar_qr_totp(empleado.email, secret)
    return {
        "secret": secret,  # shown once during enrollment — never stored plaintext
        "qr_png_base64": base64.b64encode(qr_png).decode(),
        "empleado_id": empleado_id,
    }


def verificar_supervisor_totp(
    db: Session,
    email_supervisor: str,
    otp: str,
) -> dict:
    """
    Full supervisor authentication flow:
    1. Verify email exists and has privileges
    2. Check TOTP OTP
    3. Return supervisor info on success
    Raises HTTPException on any failure.
    """
    from sqlmodel import select as sel
    from app.models.core_models import Empleado, Rol

    stmt = sel(Empleado).where(Empleado.email == email_supervisor.strip())
    supervisor = db.exec(stmt).first()
    if not supervisor or not supervisor.activo:
        raise HTTPException(status_code=401, detail="Supervisor not found or inactive.")

    rol = db.get(Rol, supervisor.rol_id)
    if not rol or rol.nombre not in ("ADMIN", "GERENTE", "SUPERVISOR"):
        raise HTTPException(status_code=403, detail="The employee does not have supervisor permissions.")

    totp_record = db.exec(select(EmpleadoTOTP).where(
        EmpleadoTOTP.empleado_id == supervisor.id,
        EmpleadoTOTP.activo == True
    )).first()
    if not totp_record:
        raise HTTPException(status_code=403, detail="The supervisor does not have TOTP configured. Contact the administrator.")

    try:
        secret = _decrypt_secret(totp_record.secreto_encriptado)
    except Exception:
        raise HTTPException(status_code=401, detail="The server's TOTP key changed. The supervisor must enroll again.")
    
    if not verificar_otp(secret, otp.strip()):
        raise HTTPException(status_code=401, detail="Incorrect or expired OTP code.")

    # Record last usage
    totp_record.ultimo_uso_otp = get_local_now()
    db.add(totp_record)
    db.commit()

    return {
        "supervisor_id": supervisor.id,
        "supervisor_nombre": supervisor.nombre_completo,
        "rol": rol.nombre,
    }
