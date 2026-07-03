import bcrypt
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Union, Any, List
from jose import jwt, JWTError
from fastapi import Header, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session
from fastapi.security import HTTPBearer
from app.models.core_models import Empleado, Rol
from app.core.timezone import get_local_now

DEV_MODE = True

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

security_bearer = HTTPBearer(auto_error=False)

SECRET_KEY = os.getenv("CORE_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

if not SECRET_KEY:
    raise RuntimeError("ERROR CRÍTICO: No se encontró CORE_SECRET_KEY en las variables de entorno.")



def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_password.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False



def create_access_token(subject: Union[str, Any], canal: str, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire = get_local_now() + expires_delta
    else:
        expire = get_local_now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "canal": canal
    }

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None



GATEWAY_SECRET = SECRET_KEY


async def validate_gateway_token(x_gateway_token: str = Header(None)):
    """
    if not x_gateway_token:
        print("[SEGURIDAD] No está el token de Gateway en la petición.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: Token de Gateway ausente en los encabezados."
        )

    if x_gateway_token != GATEWAY_SECRET:
        print(f"[SEGURIDAD] Token de Gateway incorrecto recibido: {x_gateway_token}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: Token de Gateway incorrecto o inválido."
        )
    """
    return


def verificar_rol_empleado(token: str, roles_permitidos: List[str], db: Session) -> dict:

    if not token:
        raise HTTPException(status_code=401, detail="Token de autenticación requerido.")

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Token inválido o expirado.")

    empleado_id = payload.get("sub")
    if not empleado_id:
        raise HTTPException(status_code=401, detail="Token malformado.")

    empleado = db.get(Empleado, int(empleado_id))
    if not empleado or not empleado.activo:
        raise HTTPException(status_code=401, detail="Empleado no encontrado o inactivo.")

    rol = db.get(Rol, empleado.rol_id)
    if not rol:
        raise HTTPException(status_code=403, detail="El empleado no tiene rol asignado.")

    if roles_permitidos and rol.nombre not in roles_permitidos:
        raise HTTPException(
            status_code=403,
            detail=f"Acceso denegado. Se requiere uno de los roles: {', '.join(roles_permitidos)}."
        )

    return {"empleado_id": empleado.id, "rol": rol.nombre, "empleado": empleado}