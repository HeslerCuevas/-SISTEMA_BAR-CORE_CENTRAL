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
    propina_extra: Decimal = 0.0
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
    propina_extra: float
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


class CancelarPedidoRequest(BaseModel):
    empleado_id: int
    motivo: str


from pydantic import BaseModel
from typing import List, Optional
import uuid

class DetalleItemAdicional(BaseModel):
    detalle_local_uuid: uuid.UUID
    producto_id: int
    cantidad: int
    precio_unitario: float
    monto_impuesto: float
    subtotal_linea: float

class AgregarItemsRequest(BaseModel):
    cliente_id: Optional[int] = None
    nuevo_subtotal_agregado: Decimal
    nuevo_impuesto_agregado: Decimal
    detalles_adicionales: List[DetalleItemAdicional]

class SolicitarCuentaRequest(BaseModel):
    metodo_pago_preferido: str = "EFECTIVO"
    propina_extra: Decimal = Decimal("0.0")

class ItemResumen(BaseModel):
    producto_nombre: str
    cantidad: int
    subtotal_linea: float
    estado_preparacion: str

class ResumenCuentaResponse(BaseModel):
    factura_local_uuid: uuid.UUID
    estado_cuenta: str
    subtotal_acumulado: float
    total_impuestos_acumulado: float
    propina_legal_acumulada: float
    total_general_acumulado: float
    items_consumidos: List[ItemResumen]
    propina_extra_acumulada: float

class FacturarPedidoRequest(BaseModel):
    empleado_id: int


class ModificadorItemRequest(BaseModel):
    """Instrucciones especiales para un ítem (ej: 'sin hielo', 'doble shot')."""
    descripcion: str


class ModificadorItemResponse(BaseModel):
    id: int
    detalle_pedido_uuid: uuid.UUID  # <-- REVISA QUE ESTÉ ASÍ Y NO COMO detalle_pedido_id
    descripcion: str
    fecha_registro: Optional[datetime] = None

    class Config:
        from_attributes = True

class SplitBillRequest(BaseModel):
    numero_partes: int
    montos_personalizados: Optional[List[float]] = None
    empleado_id: Optional[int] = None


class SplitBillResponse(BaseModel):
    pedido_id: int
    factura_local_uuid: Optional[str]
    total_general: Decimal
    numero_partes: int
    monto_por_parte: Decimal
    partes: List[dict]
    division_id: int
