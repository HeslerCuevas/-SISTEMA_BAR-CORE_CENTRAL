from pydantic import BaseModel, field_validator
from typing import Optional
import uuid


# ─── Schemas existentes (QR / Mobile flow) ────────────────────────────────────

class MesaVincularRequest(BaseModel):
    codigo_qr_mesa: str
    numero_mesa: int


class MesaVincularResponse(BaseModel):
    mensaje: str
    estado_mesa: str
    numero_mesa: int
    factura_local_uuid_activa: Optional[uuid.UUID] = None


class LlamarMeseroRequest(BaseModel):
    motivo_llamada: str = "ASISTENCIA_GENERAL"


class LlamarMeseroResponse(BaseModel):
    mensaje: str


# ─── Schemas administrativos ──────────────────────────────────────────────────

class MesaCreate(BaseModel):
    numero: int
    descripcion: Optional[str] = None
    capacidad: int = 4

    @field_validator('numero')
    @classmethod
    def numero_positivo(cls, v: int) -> int:
        if v < 1:
            raise ValueError('El número de mesa debe ser mayor a 0.')
        return v

    @field_validator('capacidad')
    @classmethod
    def capacidad_valida(cls, v: int) -> int:
        if v < 1:
            raise ValueError('La capacidad debe ser al menos 1.')
        return v


class MesaUpdate(BaseModel):
    numero: Optional[int] = None
    descripcion: Optional[str] = None
    capacidad: Optional[int] = None
    activo: Optional[bool] = None


class MesaAdminResponse(BaseModel):
    id: int
    numero: int
    descripcion: Optional[str] = None
    capacidad: int
    activo: bool
    qr_token: Optional[str] = None

    class Config:
        from_attributes = True