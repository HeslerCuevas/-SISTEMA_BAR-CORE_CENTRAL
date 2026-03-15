from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import datetime

class ProductoCreate(BaseModel):
    categoria_id: int
    impuesto_id: int
    sku: str
    nombre: str
    descripcion: Optional[str] = None
    precio_base: Decimal
    costo_promedio: Decimal
    es_inventariable: bool = True
    activo: bool = True

class ProductoResponse(ProductoCreate):
    id: int
    ultima_modificacion: datetime

    class Config:
        from_attributes = True