from pydantic import BaseModel, field_validator, EmailStr
from typing import Optional
import re


class EmpleadoCreate(BaseModel):
    nombre_completo: str
    documento_identidad: str
    email: str
    password_plano: str
    rol_id: int
    sucursal_id: int

    @field_validator('password_plano')
    @classmethod
    def password_segura(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres.')
        if not re.search(r'[A-Z]', v):
            raise ValueError('La contraseña debe contener al menos una mayúscula.')
        if not re.search(r'[0-9]', v):
            raise ValueError('La contraseña debe contener al menos un número.')
        return v

    @field_validator('email')
    @classmethod
    def email_valido(cls, v: str) -> str:
        if '@' not in v:
            raise ValueError('Email inválido.')
        return v.lower().strip()

    @field_validator('nombre_completo')
    @classmethod
    def nombre_no_vacio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('El nombre completo no puede estar vacío.')
        return v.strip()


class EmpleadoUpdate(BaseModel):
    nombre_completo: Optional[str] = None
    documento_identidad: Optional[str] = None
    email: Optional[str] = None
    rol_id: Optional[int] = None
    sucursal_id: Optional[int] = None
    activo: Optional[bool] = None

    @field_validator('email')
    @classmethod
    def email_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if '@' not in v:
                raise ValueError('Email inválido.')
            return v.lower().strip()
        return v

    @field_validator('nombre_completo')
    @classmethod
    def nombre_no_vacio(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v or not v.strip():
                raise ValueError('El nombre completo no puede estar vacío.')
            return v.strip()
        return v


class EmpleadoAdminResponse(BaseModel):
    id: int
    rol_id: int
    sucursal_id: int
    documento_identidad: str
    nombre_completo: str
    email: str
    activo: bool

    class Config:
        from_attributes = True


class EmpleadoDesactivarResponse(BaseModel):
    mensaje: str
    empleado_id: int
    activo: bool
