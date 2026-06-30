from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

class MovimientoCreate(BaseModel):
    producto_id: int
    empleado_id: Optional[int] = None
    tipo_movimiento: Literal["ENTRADA", "SALIDA", "AJUSTE"]
    cantidad: int = Field(..., gt=0, description="La cantidad debe ser mayor a cero")
    motivo: str
    movimiento_local_uuid: Optional[str] = None

class InventarioResponse(BaseModel):
    producto_id: int
    cantidad_disponible: int
    stock_minimo: int
    ultima_actualizacion: datetime
    ultima_modificacion: datetime

    class Config:
        from_attributes = True

class MovimientoInventarioResponse(BaseModel):
    id: int
    producto_id: int
    empleado_id: Optional[int] = None
    tipo_movimiento: str
    cantidad: int
    motivo: str
    fecha_movimiento: datetime
    movimiento_local_uuid: Optional[str] = None
    factura_local_uuid: Optional[str] = None

    class Config:
        from_attributes = True