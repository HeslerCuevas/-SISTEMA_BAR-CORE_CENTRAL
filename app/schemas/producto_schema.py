from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from decimal import Decimal
from datetime import datetime


TipoControlInventarioType = Literal["PRODUCTO", "INGREDIENTES", "NINGUNO"]


class ProductoCreate(BaseModel):
    model_config = {"populate_by_name": True}

    categoria_id: int
    impuesto_id: int
    sku: str
    nombre: str
    # Acepta tanto 'descripcion' (español) como 'description' (inglés)
    descripcion: Optional[str] = Field(default=None, alias="description", validation_alias="descripcion")
    precio_base: Decimal
    costo_promedio: Decimal
    # PRODUCTO = legacy per-unit stock | INGREDIENTES = recipe-based | NINGUNO = no tracking
    tipo_control_inventario: TipoControlInventarioType = "PRODUCTO"
    activo: bool = True
    imagen_url: Optional[str] = None

    @field_validator('precio_base')
    @classmethod
    def precio_no_negativo(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError('El precio base no puede ser negativo.')
        return v

    @field_validator('costo_promedio')
    @classmethod
    def costo_no_negativo(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError('El costo promedio no puede ser negativo.')
        return v




class ProductoUpdate(BaseModel):
    """PATCH parcial: todos los campos son opcionales."""
    categoria_id: Optional[int] = None
    impuesto_id: Optional[int] = None
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    precio_base: Optional[Decimal] = None
    costo_promedio: Optional[Decimal] = None
    tipo_control_inventario: Optional[TipoControlInventarioType] = None
    activo: Optional[bool] = None
    imagen_url: Optional[str] = None

    @field_validator('precio_base')
    @classmethod
    def precio_no_negativo(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < 0:
            raise ValueError('El precio base no puede ser negativo.')
        return v

    @field_validator('costo_promedio')
    @classmethod
    def costo_no_negativo(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < 0:
            raise ValueError('El costo promedio no puede ser negativo.')
        return v




class ProductoResponse(ProductoCreate):
    model_config = {"populate_by_name": True, "from_attributes": True}

    id: int
    tasa_impuesto: Decimal
    cantidad_disponible: Optional[int] = None
    # Re-declaramos sin alias para que el JSON de respuesta siempre use 'descripcion'
    descripcion: Optional[str] = None
    tipo_control_inventario: str
    ultima_modificacion: datetime
    imagen_url: Optional[str] = None
    id_categoria: Optional[int] = None



class CategoriaCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None

    @field_validator('nombre')
    @classmethod
    def nombre_no_vacio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('El nombre de la categoría no puede estar vacío.')
        return v.strip()


class CategoriaUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    activo: Optional[bool] = None

    @field_validator('nombre')
    @classmethod
    def nombre_no_vacio(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError('El nombre de la categoría no puede estar vacío.')
        return v.strip() if v else v


class CategoriaResponse(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    activo: bool

    class Config:
        from_attributes = True


class ImpuestoCreate(BaseModel):
    nombre: str
    tasa_porcentaje: Decimal

    @field_validator('tasa_porcentaje')
    @classmethod
    def tasa_valida(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError('La tasa de impuesto no puede ser negativa.')
        if v > 100:
            raise ValueError('La tasa de impuesto no puede superar el 100%.')
        return v

    @field_validator('nombre')
    @classmethod
    def nombre_no_vacio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('El nombre del impuesto no puede estar vacío.')
        return v.strip()


class ImpuestoUpdate(BaseModel):
    nombre: Optional[str] = None
    tasa_porcentaje: Optional[Decimal] = None
    activo: Optional[bool] = None

    @field_validator('tasa_porcentaje')
    @classmethod
    def tasa_valida(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None:
            if v < 0:
                raise ValueError('La tasa de impuesto no puede ser negativa.')
            if v > 100:
                raise ValueError('La tasa de impuesto no puede superar el 100%.')
        return v


class ImpuestoResponse(BaseModel):
    id: int
    nombre: str
    tasa_porcentaje: float
    activo: bool

    class Config:
        from_attributes = True

