from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class PedidoCreate(BaseModel):
    empleado_id: Optional[int] = None
    cliente_id: Optional[int] = None
    canal_origen: str = Field(..., description="Debe ser: CAJA, MOVIL, WEB", pattern="^(CAJA|MOVIL|WEB)$")
    mesa: Optional[int] = None


class DetallePedidoCreate(BaseModel):
    producto_id: int
    cantidad: int = Field(..., gt=0, description="La cantidad debe ser mayor a cero")


class PedidoResponse(BaseModel):
    id: int
    cliente_id: Optional[int]
    canal_origen: str
    mesa: Optional[int]
    estado: str
    subtotal: Decimal = None
    total_impuestos: Decimal = None
    total_general: Decimal = None
    fecha_creacion: datetime

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

    class Config:
        from_attributes = True

