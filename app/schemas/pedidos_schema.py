from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from decimal import Decimal
import uuid

class DetallePedidoCreate(BaseModel):
    producto_id: int
    cantidad: int = Field(..., gt=0, description="La cantidad debe ser mayor a cero")
    detalle_local_uuid: Optional[uuid.UUID] = None

class PedidoCreate(BaseModel):
    empleado_id: Optional[int] = None
    cliente_id: Optional[int] = None
    canal_origen: Literal["CAJA", "MOVIL", "WEB"]
    mesa: Optional[int] = None
    factura_local_uuid: Optional[uuid.UUID] = None
    detalles: list[DetallePedidoCreate]

class PedidoResponse(BaseModel):
    id: int
    cliente_id: Optional[int]
    canal_origen: str
    mesa: Optional[int]
    estado: str
    propina_legal: Decimal
    subtotal: Decimal
    total_impuestos: Decimal
    total_general: Decimal
    fecha_creacion: datetime
    factura_local_uuid: Optional[uuid.UUID]

    class Config:
        from_attributes = True

class DetallePedidoResponse(BaseModel):
    id: int
    producto_id: int
    cantidad: int
    precio_unitario_historico: Decimal
    impuesto_historico: Decimal
    monto_impuesto: Decimal
    subtotal_linea: Decimal
    detalle_local_uuid: Optional[uuid.UUID]

    class Config:
        from_attributes = True
