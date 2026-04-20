import bcrypt
import os
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
from fastapi import Header, HTTPException, status

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
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


GATEWAY_SECRET = os.getenv("CORE_SECRET_KEY")


async def validate_gateway_token(x_gateway_token: str = Header(None)):
    if x_gateway_token != GATEWAY_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: Token de Gateway inválido"
        )