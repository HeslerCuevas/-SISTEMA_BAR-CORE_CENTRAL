import bcrypt
import os
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt  # Asegúrate de tener instalado python-jose
from fastapi import Header, HTTPException, status

# --- CONFIGURACIÓN DE SEGURIDAD ---
# Usamos la misma secret key para encriptar los JWT
SECRET_KEY = os.getenv("CORE_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # El token durará 24 horas

if not SECRET_KEY:
    raise RuntimeError("ERROR CRÍTICO: No se encontró CORE_SECRET_KEY en las variables de entorno.")


# --- LÓGICA DE CONTRASEÑAS (BCRYPT) ---

def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_password.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


# --- LÓGICA DE TOKENS (JWT) ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Genera un token JWT firmado para que el cliente lo use en sus peticiones.
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # Añadimos la fecha de expiración al payload
    to_encode.update({"exp": expire})

    # Firmamos el token con nuestra SECRET_KEY
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# --- SEGURIDAD INTERNA (GATEWAY -> CORE) ---

GATEWAY_SECRET = os.getenv("CORE_SECRET_KEY")  # Usamos la misma o una distinta si prefieres


async def validate_gateway_token(x_gateway_token: str = Header(None)):
    if x_gateway_token != GATEWAY_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: Token de Gateway inválido"
        )