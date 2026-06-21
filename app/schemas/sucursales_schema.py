from pydantic import BaseModel, field_validator
from typing import Optional


class SucursalCreate(BaseModel):
    nombre: str
    direccion: Optional[str] = None

    @field_validator('nombre')
    @classmethod
    def nombre_no_vacio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('El nombre de la sucursal no puede estar vacío.')
        return v.strip()


class SucursalUpdate(BaseModel):
    nombre: Optional[str] = None
    direccion: Optional[str] = None

    @field_validator('nombre')
    @classmethod
    def nombre_no_vacio(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError('El nombre de la sucursal no puede estar vacío.')
        return v.strip() if v else v


class SucursalResponse(BaseModel):
    id: int
    nombre: str
    direccion: Optional[str] = None
    activo: bool

    class Config:
        from_attributes = True
