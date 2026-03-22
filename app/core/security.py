import bcrypt
from fastapi import Header, HTTPException, status
import os

def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_password.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


GATEWAY_SECRET = os.getenv("CORE_SECRET_KEY", "v87n34v87tnv39kb23nv7y37vg34v309ung7477")

async def validate_gateway_token(x_gateway_token: str = Header(None)):
    if x_gateway_token != GATEWAY_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para acceder directamente al CORE. Usa el Gateway."
        )