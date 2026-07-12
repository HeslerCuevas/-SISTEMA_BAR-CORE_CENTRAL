from pydantic import BaseModel
from decimal import Decimal
from typing import Optional, List
from datetime import date, datetime

# ─── Existing schemas (unchanged) ────────────────────────────────────────────

class VentasDiaResponse(BaseModel):
    propina_legal: Decimal
    subtotal: Decimal
    total_impuestos: Decimal
    total_general: Decimal
    conteo_pedidos: int

    class Config:
        from_attributes = True


class RankingProductosResponse(BaseModel):
    nombre: str
    cantidad_vendida: int

    class Config:
        from_attributes = True


class AlertaStockResponse(BaseModel):
    """Legacy: product-level stock alert (for PRODUCTO type products)."""
    producto_id: int
    sku: str
    nombre: str
    cantidad_disponible: int
    stock_minimo: int

    class Config:
        from_attributes = True


class AlertaIngredienteResponse(BaseModel):
    """Ingredient below its minimum threshold — main alert for ingredient-based system."""
    id: int
    nombre: str
    unidad_medida: str
    cantidad_actual: Decimal
    cantidad_minima: Decimal
    cantidad_reorden: Decimal
    deficit: Decimal  # cantidad_reorden - cantidad_actual (>= 0)

    class Config:
        from_attributes = True


# ─── New dashboard / graph schemas ───────────────────────────────────────────

class VentasPeriodoResponse(BaseModel):
    """Aggregate sales totals for a given date range."""
    fecha_inicio: date
    fecha_fin: date
    subtotal: Decimal
    total_impuestos: Decimal
    propina_legal: Decimal
    total_general: Decimal
    conteo_pedidos: int

    class Config:
        from_attributes = True


class VentasDiaSerie(BaseModel):
    """Single point in a daily revenue time-series."""
    fecha: date
    subtotal: Decimal
    total_general: Decimal
    conteo_pedidos: int

    class Config:
        from_attributes = True


class VentasHoraSerie(BaseModel):
    """Single point in an hourly order-distribution chart."""
    hora: int          # 0-23
    conteo_pedidos: int
    total_general: Decimal

    class Config:
        from_attributes = True


class RankingProductosPeriodoResponse(BaseModel):
    """Top-selling product entry, filterable by date range."""
    producto_id: int
    nombre: str
    categoria: str
    cantidad_vendida: int
    ingreso_total: Decimal

    class Config:
        from_attributes = True


class VentasCanalResponse(BaseModel):
    """Revenue breakdown per sales channel."""
    canal: str
    conteo_pedidos: int
    total_general: Decimal

    class Config:
        from_attributes = True


class VentasCategoriaResponse(BaseModel):
    """Revenue grouped by product category."""
    categoria_id: int
    categoria: str
    conteo_productos_vendidos: int
    ingreso_total: Decimal

    class Config:
        from_attributes = True


class KpisGeneralesResponse(BaseModel):
    """Single scoreboard object for the admin/manager dashboard."""
    # Sales today
    ventas_hoy_total: Decimal
    ventas_hoy_conteo: int
    # Open orders
    pedidos_abiertos: int
    pedidos_por_facturar: int
    # Stock alerts
    productos_stock_bajo: int
    ingredientes_stock_bajo: int
    # Promos
    promociones_activas: int

    class Config:
        from_attributes = True


class PedidoAbiertoResumen(BaseModel):
    """Summary of a single open order for the dashboard."""
    id: int
    factura_local_uuid: Optional[str]
    canal_origen: str
    mesa: Optional[int]
    estado: str
    total_general: Decimal
    fecha_creacion: datetime
    empleado_id: Optional[int]

    class Config:
        from_attributes = True


class MovimientoRecienteResponse(BaseModel):
    """Recent ingredient movement for an activity-feed widget."""
    id: int
    ingrediente_id: int
    ingrediente_nombre: str
    tipo_movimiento: str
    cantidad: Decimal
    unidad_medida: str
    fecha_movimiento: datetime
    empleado_id: Optional[int]
    notas: Optional[str]

    class Config:
        from_attributes = True


class PromocionActivaResumen(BaseModel):
    """Active promotion summary for the dashboard."""
    id: int
    nombre: str
    tipo_descuento: str
    valor: Decimal
    aplica_a: str
    tipo_aplicacion: str
    usos_hoy: int
    descuento_total_hoy: Decimal

    class Config:
        from_attributes = True
