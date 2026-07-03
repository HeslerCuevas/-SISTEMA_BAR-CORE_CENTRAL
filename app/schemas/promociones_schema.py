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
    precio_minimo_final: Optional[Decimal] = None
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
    precio_minimo_final: Optional[Decimal] = None
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
    tipo_aplicacion: str
    aplica_happy_hour: bool
    hora_inicio_hh: Optional[str] = None
    hora_fin_hh: Optional[str] = None
    fecha_creacion: datetime
    precio_minimo_final: Optional[Decimal] = None
    
    producto_ids: Optional[List[int]] = []
    categoria_ids: Optional[List[int]] = []

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


# ── New Redesign Schemas ──────────────────────────────────────────────────────

class PromocionCreateExtended(PromocionCreate):
    """Extended creation schema allowing specific application types."""
    tipo_aplicacion: str = "AUTOMATICA"

    @field_validator('tipo_aplicacion')
    @classmethod
    def tipo_valido(cls, v: str) -> str:
        valid = ["AUTOMATICA", "ELEGIBILIDAD", "CODIGO_PROMO", "MANUAL"]
        if v not in valid:
            raise ValueError(f'tipo_aplicacion debe ser uno de: {valid}')
        return v


class SupervisorAuthRequest(BaseModel):
    email: str
    otp: str


class SupervisorAuthResponse(BaseModel):
    ok: bool = True
    supervisor_id: int
    supervisor_nombre: str
    rol: str


class TOTPEnrollResponse(BaseModel):
    secret: str
    qr_png_base64: str
    empleado_id: int


class PromocionElegibilidadConfig(BaseModel):
    etiqueta_identificador: str = "Credential ID"
    requiere_identificador: bool = True


class CodigoPromoValidarRequest(BaseModel):
    codigo: str
    subtotal: Decimal
    cliente_id: Optional[int] = None


class CodigoPromoValidarResponse(BaseModel):
    valido: bool
    codigo_id: Optional[int] = None
    promocion_id: Optional[int] = None
    nombre: Optional[str] = None
    tipo_descuento: Optional[str] = None
    valor: Optional[Decimal] = None
    tipo_aplicacion: str = "CODIGO_PROMO"


class AplicacionPromocionSync(BaseModel):
    """Payload for syncing an audit record from CAJA to CORE."""
    factura_uuid: Optional[str] = None
    promocion_id: Optional[int] = None
    nombre_promocion_snap: str
    tipo_aplicacion: str
    empleado_id: Optional[int] = None
    empleado_autorizador_id: Optional[int] = None
    identificador_capturado: Optional[str] = None
    monto_descuento: Decimal
    terminal: Optional[str] = None
    notas: Optional[str] = None


class SupervisorSessionSync(BaseModel):
    id: str
    supervisor_id: int
    cajero_id: int
    terminal: str
    inicio: datetime
    fin: datetime
    motivo_fin: str
