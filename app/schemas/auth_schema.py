from pydantic import BaseModel, field_validator
from typing import Optional
import re


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


# ─── Cambio de contraseña ─────────────────────────────────────────────────────

class CambioPasswordEmpleadoRequest(BaseModel):
    """Para que un empleado cambie su propia contraseña."""
    password_actual: str
    password_nuevo: str
    password_nuevo_confirmacion: str

    @field_validator('password_nuevo')
    @classmethod
    def password_segura(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('La nueva contraseña debe tener al menos 8 caracteres.')
        if not re.search(r'[A-Z]', v):
            raise ValueError('La nueva contraseña debe contener al menos una mayúscula.')
        if not re.search(r'[0-9]', v):
            raise ValueError('La nueva contraseña debe contener al menos un número.')
        return v

    @field_validator('password_nuevo_confirmacion')
    @classmethod
    def confirmacion_coincide(cls, v: str, info) -> str:
        if 'password_nuevo' in info.data and v != info.data['password_nuevo']:
            raise ValueError('Las contraseñas nuevas no coinciden.')
        return v


class CambioPasswordAdminRequest(BaseModel):
    """Para que un administrador cambie la contraseña de otro empleado."""
    nuevo_password: str

    @field_validator('nuevo_password')
    @classmethod
    def password_segura(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres.')
        if not re.search(r'[A-Z]', v):
            raise ValueError('La contraseña debe contener al menos una mayúscula.')
        if not re.search(r'[0-9]', v):
            raise ValueError('La contraseña debe contener al menos un número.')
        return v


class CambioPasswordClienteRequest(BaseModel):
    """Para que un cliente cambie su propia contraseña (requiere actual)."""
    password_actual: str
    password_nuevo: str
    password_nuevo_confirmacion: str

    @field_validator('password_nuevo')
    @classmethod
    def password_segura(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('La nueva contraseña debe tener al menos 8 caracteres.')
        if not re.search(r'[A-Z]', v):
            raise ValueError('La nueva contraseña debe contener al menos una mayúscula.')
        if not re.search(r'[0-9]', v):
            raise ValueError('La nueva contraseña debe contener al menos un número.')
        return v

    @field_validator('password_nuevo_confirmacion')
    @classmethod
    def confirmacion_coincide(cls, v: str, info) -> str:
        if 'password_nuevo' in info.data and v != info.data['password_nuevo']:
            raise ValueError('Las contraseñas nuevas no coinciden.')
        return v


class SolicitarResetRequest(BaseModel):
    email: str


class ConfirmarResetRequest(BaseModel):
    token: str
    password_nuevo: str
    password_nuevo_confirmacion: str

    @field_validator('password_nuevo')
    @classmethod
    def password_segura(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres.')
        if not re.search(r'[A-Z]', v):
            raise ValueError('La contraseña debe contener al menos una mayúscula.')
        if not re.search(r'[0-9]', v):
            raise ValueError('La contraseña debe contener al menos un número.')
        return v

    @field_validator('password_nuevo_confirmacion')
    @classmethod
    def confirmacion_coincide(cls, v: str, info) -> str:
        if 'password_nuevo' in info.data and v != info.data['password_nuevo']:
            raise ValueError('Las contraseñas nuevas no coinciden.')
        return v


class PasswordResetResponse(BaseModel):
    mensaje: str