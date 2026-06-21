from pydantic import BaseModel, field_validator, model_validator
from typing import Optional, List
from datetime import datetime


TIPOS_NCF_VALIDOS = ["B01", "B02", "B14", "B15", "B16"]


class SecuenciaNcfCreate(BaseModel):
    tipo_ncf: str
    serie: str
    rango_desde: int
    rango_hasta: int
    fecha_vencimiento: datetime
    sucursal_id: Optional[int] = None

    @field_validator('tipo_ncf')
    @classmethod
    def tipo_valido(cls, v: str) -> str:
        if v not in TIPOS_NCF_VALIDOS:
            raise ValueError(f'tipo_ncf debe ser uno de: {TIPOS_NCF_VALIDOS}')
        return v

    @model_validator(mode='after')
    def validar_rango(self) -> 'SecuenciaNcfCreate':
        if self.rango_desde >= self.rango_hasta:
            raise ValueError('rango_desde debe ser menor a rango_hasta.')
        if self.rango_desde < 1:
            raise ValueError('rango_desde debe ser >= 1.')
        return self


class SecuenciaNcfUpdate(BaseModel):
    fecha_vencimiento: Optional[datetime] = None
    activo: Optional[bool] = None


class SecuenciaNcfResponse(BaseModel):
    id: int
    tipo_ncf: str
    serie: str
    rango_desde: int
    rango_hasta: int
    secuencia_actual: int
    fecha_vencimiento: datetime
    activo: bool
    sucursal_id: Optional[int] = None
    fecha_creacion: datetime
    disponibles: int  # rango_hasta - secuencia_actual
    porcentaje_uso: float

    class Config:
        from_attributes = True


class NcfAsignacionRequest(BaseModel):
    pedido_id: Optional[int] = None
    empleado_id: Optional[int] = None
    sucursal_id: Optional[int] = None
    tipo_ncf: str = "B02"


class NcfAsignadoResponse(BaseModel):
    ncf_asignado: str
    tipo_ncf: str
    serie: str
    secuencia_id: int
    pedido_id: Optional[int] = None
    fecha_asignacion: datetime


class HistorialNcfResponse(BaseModel):
    id: int
    secuencia_id: int
    ncf_asignado: str
    pedido_id: Optional[int] = None
    empleado_id: Optional[int] = None
    fecha_asignacion: datetime

    class Config:
        from_attributes = True
