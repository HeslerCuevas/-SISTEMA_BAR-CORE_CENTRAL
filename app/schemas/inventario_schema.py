from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class MovimientoCreate(BaseModel):
    producto_id: int
    empleado_id: Optional[int] = None
    tipo_movimiento: str = Field(..., description="Debe ser: ENTRADA, SALIDA o AJUSTE")
    cantidad: int = Field(..., gt=0, description="La cantidad debe ser mayor a cero")
    motivo: str

class InventarioResponse(BaseModel):
    producto_id: int
    cantidad_disponible: int
    stock_minimo: int
    ultima_actualizacion: datetime

    class Config:
        from_attributes = True