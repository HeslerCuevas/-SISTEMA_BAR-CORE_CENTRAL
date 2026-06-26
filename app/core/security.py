import bcrypt
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Union, Any, List
from jose import jwt, JWTError
from fastapi import Header, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

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
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

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


def get_current_empleado(
        token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado o token expirado. Proporcione un Bearer token válido.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token_obj or not token_obj.credentials:
        raise credentials_exception

    token = token_obj.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise credentials_exception

    empleado_id = payload.get("sub")
    if empleado_id is None:
        raise credentials_exception

    return {"empleado_id": int(empleado_id), "canal": payload.get("canal"), "payload": payload}


def get_current_empleado_con_rol(session_getter):
    pass


def requerir_rol(*roles_permitidos: str):
    """
    Factoría de dependencias para control de acceso por rol.
    """
    from app.db.database import get_session
    from app.models.core_models import Empleado, Rol

    async def _check_rol(
            token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    ):
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado o token expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        forbidden_exception = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Acceso denegado. Roles permitidos: {', '.join(roles_permitidos)}."
        )

        # 3. Extraemos el string del token (.credentials) también aquí
        if not token_obj or not token_obj.credentials:
            raise credentials_exception

        token = token_obj.credentials
        payload = decode_access_token(token)

        if payload is None:
            raise credentials_exception

        empleado_id = payload.get("sub")
        if not empleado_id:
            raise credentials_exception

        with Session(next((s for s in []), None) or __import__('app.db.database', fromlist=['engine']).engine) as db:
            empleado = db.get(Empleado, int(empleado_id))
            if not empleado or not empleado.activo:
                raise credentials_exception
            rol = db.get(Rol, empleado.rol_id)
            if not rol or rol.nombre not in roles_permitidos:
                raise forbidden_exception
            return {"empleado_id": empleado.id, "rol": rol.nombre}

    return _check_rol


def verificar_rol_empleado(token: str, roles_permitidos: List[str], db: Session) -> dict:
    """
    Utilidad síncrona para verificar el rol de un empleado a partir de su token.
    Se usa directamente dentro de los endpoints.
    Retorna {empleado_id, rol, empleado} o lanza HTTPException.
    """
    if DEV_MODE and token == "mock_dev_token":
        # Simula que eres el empleado ID 1 y tienes rol de ADMIN
        return {"empleado_id": 1, "rol": "ADMIN", "empleado": None}

    from app.models.core_models import Empleado, Rol

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