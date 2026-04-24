from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    empleado_id: int
    nombre: str
    rol: str
    sucursal_id: int
    activo: bool

    class Config:
        from_attributes = True

class EmpleadoResponse(BaseModel):
    id: int
    rol_id: int
    sucursal_id: int
    documento_identidad: str
    nombre_completo: str
    email: str
    password_hash: str
    activo: bool

    class Config:
        from_attributes = True


class ClienteRegistroRequest(BaseModel):
    nombre_completo: str
    email: str
    telefono: Optional[str] = None
    password_plano: str

class ClienteRegistroResponse(BaseModel):
    mensaje: str
    cliente_id: int
    email: str

class ClienteLoginRequest(BaseModel):
    email: str
    password_plano: str

class ClienteLoginResponse(BaseModel):
    access_token: str
    token_type: str
    canal: str
    cliente_id: int
    nombre_completo: str