from pydantic import BaseModel, Field, field_validator
from typing import Optional
import uuid


# ─── SCHEMAS MÓVILES (Flujo QR Protegido) ─────────────────────────────────────

class MesaVincularRequest(BaseModel):
    # Se elimina 'numero_mesa' para evitar que usuarios adivinen IDs de mesas remotamente
    codigo_qr_mesa: str = Field(..., description="Token seguro extraído del código QR de la mesa física")


class MesaVincularResponse(BaseModel):
    mensaje: str
    estado_mesa: str
    numero_mesa: int
    factura_local_uuid_activa: Optional[uuid.UUID] = None


class LlamarMeseroRequest(BaseModel):
    # Obligatorio para asegurar presencia física al llamar al personal
    qr_token: str = Field(..., description="Token de validación del QR de la mesa")
    motivo_llamada: str = Field(default="ASISTENCIA_GENERAL", description="Ej: CUENTA, ORDENAR, ASISTENCIA_GENERAL")


class LlamarMeseroResponse(BaseModel):
    mensaje: str


# ─── SCHEMAS ADMINISTRATIVOS (CRUD CORE) ──────────────────────────────────────

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
    qr_token: Optional[str] = None # Expone el token generado para la impresión del QR físico

    class Config:
        from_attributes = True