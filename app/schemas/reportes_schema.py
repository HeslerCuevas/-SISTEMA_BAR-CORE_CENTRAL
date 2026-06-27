from pydantic import BaseModel
from decimal import Decimal
from typing import Optional

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