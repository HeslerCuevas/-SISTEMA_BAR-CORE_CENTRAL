from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ClienteAdminResponse(BaseModel):
    id: int
    nombre_completo: str
    email: str
    telefono: Optional[str] = None
    fecha_registro: datetime
    activo: bool

    class Config:
        from_attributes = True


class ClienteListResponse(BaseModel):
    total: int
    clientes: List[ClienteAdminResponse]


class ClienteEstadoResponse(BaseModel):
    mensaje: str
    cliente_id: int
    activo: bool
