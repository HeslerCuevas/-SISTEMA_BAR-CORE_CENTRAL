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
    tasa_impuesto: Decimal
    cantidad_disponible: int
    ultima_modificacion: datetime

    class Config:
        from_attributes = True

class CategoriaResponse(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    activo: bool