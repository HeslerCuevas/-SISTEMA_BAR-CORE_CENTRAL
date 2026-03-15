from pydantic import BaseModel
from decimal import Decimal

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
    nombre: str
    cantidad_disponible: int
    stock_minimo: int

    class Config:
        from_attributes = True