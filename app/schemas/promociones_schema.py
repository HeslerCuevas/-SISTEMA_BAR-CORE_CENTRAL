from pydantic import BaseModel, field_validator, model_validator
from typing import Optional, List
from decimal import Decimal
from datetime import datetime


TIPOS_DESCUENTO = ["PORCENTAJE", "MONTO_FIJO"]
APLICA_A_OPCIONES = ["TODOS", "PRODUCTOS", "CATEGORIAS"]


class PromocionCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    tipo_descuento: str
    valor: Decimal
    fecha_inicio: datetime
    fecha_fin: Optional[datetime] = None
    prioridad: int = 0
    aplica_a: str = "TODOS"
    aplica_happy_hour: bool = False
    hora_inicio_hh: Optional[str] = None
    hora_fin_hh: Optional[str] = None
    producto_ids: Optional[List[int]] = None
    categoria_ids: Optional[List[int]] = None

    @field_validator('tipo_descuento')
    @classmethod
    def tipo_valido(cls, v: str) -> str:
        if v not in TIPOS_DESCUENTO:
            raise ValueError(f'tipo_descuento debe ser uno de: {TIPOS_DESCUENTO}')
        return v

    @field_validator('aplica_a')
    @classmethod
    def aplica_valido(cls, v: str) -> str:
        if v not in APLICA_A_OPCIONES:
            raise ValueError(f'aplica_a debe ser uno de: {APLICA_A_OPCIONES}')
        return v

    @field_validator('valor')
    @classmethod
    def valor_positivo(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError('El valor del descuento debe ser mayor a 0.')
        return v

    @model_validator(mode='after')
    def validar_porcentaje(self) -> 'PromocionCreate':
        if self.tipo_descuento == 'PORCENTAJE' and self.valor > 100:
            raise ValueError('El porcentaje de descuento no puede superar el 100%.')
        if self.aplica_happy_hour:
            if not self.hora_inicio_hh or not self.hora_fin_hh:
                raise ValueError('Se requieren hora_inicio_hh y hora_fin_hh para Happy Hour.')
        return self


class PromocionUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    tipo_descuento: Optional[str] = None
    valor: Optional[Decimal] = None
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None
    prioridad: Optional[int] = None
    aplica_a: Optional[str] = None
    aplica_happy_hour: Optional[bool] = None
    hora_inicio_hh: Optional[str] = None
    hora_fin_hh: Optional[str] = None
    activo: Optional[bool] = None
    producto_ids: Optional[List[int]] = None
    categoria_ids: Optional[List[int]] = None


class PromocionResponse(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    tipo_descuento: str
    valor: Decimal
    fecha_inicio: datetime
    fecha_fin: Optional[datetime] = None
    activo: bool
    prioridad: int
    aplica_a: str
    aplica_happy_hour: bool
    hora_inicio_hh: Optional[str] = None
    hora_fin_hh: Optional[str] = None
    fecha_creacion: datetime

    class Config:
        from_attributes = True


class PromocionAplicadaResponse(BaseModel):
    """Respuesta al evaluar qué promociones aplican a un contexto dado."""
    promocion_id: int
    nombre: str
    tipo_descuento: str
    valor: Decimal
    aplica_happy_hour: bool
    monto_descuento_calculado: Decimal
