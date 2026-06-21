from pydantic import BaseModel, field_validator
from typing import Optional


class RolCreate(BaseModel):
    nombre: str

    @field_validator('nombre')
    @classmethod
    def nombre_valido(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('El nombre del rol no puede estar vacío.')
        return v.strip().upper()


class RolUpdate(BaseModel):
    nombre: str

    @field_validator('nombre')
    @classmethod
    def nombre_valido(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('El nombre del rol no puede estar vacío.')
        return v.strip().upper()


class RolResponse(BaseModel):
    id: int
    nombre: str

    class Config:
        from_attributes = True
