from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    nombre: str
    rol: str
    sucursal_id: int
    empleado_id: int

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