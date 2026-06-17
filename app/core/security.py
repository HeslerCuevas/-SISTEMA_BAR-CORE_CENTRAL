import bcrypt
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Union, Any, List
from jose import jwt, JWTError
from fastapi import Header, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select

SECRET_KEY = os.getenv("CORE_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

if not SECRET_KEY:
    raise RuntimeError("ERROR CRÍTICO: No se encontró CORE_SECRET_KEY en las variables de entorno.")


# ─── Hashing ───────────────────────────────────────────────────────────────────

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


# ─── JWT ──────────────────────────────────────────────────────────────────────

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
    """Decodifica un JWT y retorna el payload, o None si es inválido/expirado."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# ─── Gateway Token ────────────────────────────────────────────────────────────

GATEWAY_SECRET = SECRET_KEY


async def validate_gateway_token(x_gateway_token: str = Header(None)):
    if not x_gateway_token or x_gateway_token != GATEWAY_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: Token de Gateway inválido o ausente."
        )


# ─── Dependencias de Autenticación de Empleados ───────────────────────────────

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_empleado(
    token: Optional[str] = Depends(oauth2_scheme),
):
    """
    Dependencia que valida el Bearer JWT del empleado.
    Retorna dict con {empleado_id, canal, rol_id} extraído del token.
    Lanza 401 si el token es inválido o ausente.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado o token expirado. Proporcione un Bearer token válido.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    empleado_id = payload.get("sub")
    if empleado_id is None:
        raise credentials_exception

    return {"empleado_id": int(empleado_id), "canal": payload.get("canal"), "payload": payload}


def get_current_empleado_con_rol(session_getter):
    """
    Factoría que retorna una dependencia que valida el Bearer JWT
    y además carga el rol del empleado desde la BD.
    Uso: empleado_rol = Depends(get_current_empleado_con_rol(get_session))
    """
    # Esta función se usa dentro de los routers directamente para mayor control.
    pass


def requerir_rol(*roles_permitidos: str):
    """
    Factoría de dependencias para control de acceso por rol.

    Uso en router:
        @router.post("/", dependencies=[Depends(requerir_rol("ADMIN", "GERENTE"))])

    Requiere que el endpoint también tenga:
        empleado_info: dict = Depends(get_current_empleado)

    NOTA: Esta dependencia obtiene el empleado del token JWT y verifica su rol
    en la base de datos en cada request.
    """
    from app.db.database import get_session
    from app.models.core_models import Empleado, Rol

    async def _check_rol(
        token: Optional[str] = Depends(oauth2_scheme),
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

        if not token:
            raise credentials_exception

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