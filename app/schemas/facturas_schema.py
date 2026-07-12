from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
import uuid


# ─── List endpoint ────────────────────────────────────────────────────────────

class FacturaListItem(BaseModel):
    """Compact row returned by GET /facturas/ — designed for paginated tables."""
    id: int
    factura_local_uuid: Optional[str]
    fecha_creacion: datetime
    estado: str
    canal_origen: str
    mesa: Optional[int]
    subtotal: Decimal
    total_impuestos: Decimal
    propina_legal: Decimal
    propina_extra: Decimal
    total_general: Decimal
    empleado_id: Optional[int]
    empleado_nombre: Optional[str]
    cliente_id: Optional[int]

    class Config:
        from_attributes = True


# ─── Header detail ────────────────────────────────────────────────────────────

class FacturaDetalleResponse(BaseModel):
    """Full header detail for a single order/invoice."""
    id: int
    factura_local_uuid: Optional[str]
    fecha_creacion: datetime
    estado: str
    canal_origen: str
    mesa: Optional[int]
    # Financial breakdown
    subtotal: Decimal
    total_impuestos: Decimal
    propina_legal: Decimal
    propina_extra: Decimal
    total_general: Decimal
    # Who processed it
    empleado_id: Optional[int]
    empleado_nombre: Optional[str]
    # Client (optional)
    cliente_id: Optional[int]
    cliente_nombre: Optional[str]

    class Config:
        from_attributes = True


# ─── Line items ───────────────────────────────────────────────────────────────

class FacturaItemResponse(BaseModel):
    """A single line item (DetallePedido) within an invoice."""
    detalle_id: int
    producto_id: int
    producto_nombre: str
    sku: str
    cantidad: int
    precio_unitario_historico: Decimal
    impuesto_historico: Decimal   # % at time of sale
    monto_impuesto: Decimal       # absolute tax amount for this line
    subtotal_linea: Decimal       # qty * price (pre-tax)
    detalle_local_uuid: Optional[str]

    class Config:
        from_attributes = True


# ─── Applied promotions ───────────────────────────────────────────────────────

class FacturaPromocionResponse(BaseModel):
    """Promotion applied to an invoice."""
    aplicacion_id: int
    promocion_id: Optional[int]
    nombre_promocion: str
    tipo_aplicacion: str
    monto_descuento: Decimal
    empleado_id: Optional[int]
    empleado_autorizador_id: Optional[int]
    identificador_capturado: Optional[str]
    notas: Optional[str]
    fecha_hora: datetime

    class Config:
        from_attributes = True


# ─── All-in-one view ─────────────────────────────────────────────────────────

class FacturaCompletaResponse(BaseModel):
    """
    Merged invoice object with header + items + promotions applied.
    Ideal for receipt printing or full invoice display.
    """
    # Header
    id: int
    factura_local_uuid: Optional[str]
    fecha_creacion: datetime
    estado: str
    canal_origen: str
    mesa: Optional[int]
    # Staff & client
    empleado_id: Optional[int]
    empleado_nombre: Optional[str]
    cliente_id: Optional[int]
    cliente_nombre: Optional[str]
    # Financials
    subtotal: Decimal
    total_impuestos: Decimal
    propina_legal: Decimal
    propina_extra: Decimal
    total_general: Decimal
    # Related data
    items: List[FacturaItemResponse]
    promociones: List[FacturaPromocionResponse]
    total_descuentos: Decimal     # sum of all monto_descuento in promociones

    class Config:
        from_attributes = True
