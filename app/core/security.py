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
    raise RuntimeError("CRITICAL ERROR: CORE_SECRET_KEY was not found in environment variables.")



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
        print("[SECURITY] Gateway token is missing from the request.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Gateway token is missing from the headers."
        )

    if x_gateway_token != GATEWAY_SECRET:
        print(f"[SECURITY] Incorrect Gateway token received: {x_gateway_token}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Incorrect or invalid Gateway token."
        )
    """
    return


def verificar_rol_empleado(token: str, roles_permitidos: List[str], db: Session) -> dict:

    if not token:
        raise HTTPException(status_code=401, detail="Authentication token required.")

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    empleado_id = payload.get("sub")
    if not empleado_id:
        raise HTTPException(status_code=401, detail="Malformed token.")

    empleado = db.get(Empleado, int(empleado_id))
    if not empleado or not empleado.activo:
        raise HTTPException(status_code=401, detail="Employee not found or inactive.")

    rol = db.get(Rol, empleado.rol_id)
    if not rol:
        raise HTTPException(status_code=403, detail="The employee has no assigned role.")

    if roles_permitidos and rol.nombre not in roles_permitidos:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied. One of the following roles is required: {', '.join(roles_permitidos)}."
        )

    return {"empleado_id": empleado.id, "rol": rol.nombre, "empleado": empleado}
