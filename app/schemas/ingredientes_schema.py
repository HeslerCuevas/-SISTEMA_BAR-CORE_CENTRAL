"""
Pydantic schemas for the Ingredient Inventory System.

Covers:
    - Ingredient categories (CategoriaIngrediente)
    - Ingredients (Ingrediente)
    - Product recipes / BOM (RecetaProducto + ComponenteReceta)
    - Ingredient movements (MovimientoIngrediente)
    - Availability and reporting
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.logic.unit_converter import VALID_UNITS

# ─── Valid units as a Literal for schema validation ───────────────────────────

UnidadMedidaType = Literal["ml", "l", "g", "kg", "unidad", "pieza", "botella", "lata"]

# ─── Manual movement types (excludes auto types CONSUMO_VENTA / DEVOLUCION) ──

TipoMovimientoManual = Literal[
    "COMPRA", "AJUSTE_MANUAL", "DESPERDICIO", "CORRECCION", "CARGA_INICIAL"
]


# =============================================================================
# CATEGORIA INGREDIENTE
# =============================================================================

class CategoriaIngredienteCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    descripcion: Optional[str] = Field(default=None, max_length=500)

    @field_validator("nombre")
    @classmethod
    def nombre_no_vacio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El nombre no puede estar vacío.")
        return v


class CategoriaIngredienteUpdate(BaseModel):
    nombre: Optional[str] = Field(default=None, max_length=100)
    descripcion: Optional[str] = Field(default=None, max_length=500)
    activo: Optional[bool] = None

    @field_validator("nombre")
    @classmethod
    def nombre_no_vacio(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("El nombre no puede estar vacío.")
        return v


class CategoriaIngredienteResponse(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    activo: bool

    class Config:
        from_attributes = True


# =============================================================================
# INGREDIENTE
# =============================================================================

class IngredienteCreate(BaseModel):
    categoria_id: int
    nombre: str = Field(..., min_length=1, max_length=150)
    descripcion: Optional[str] = Field(default=None, max_length=500)
    unidad_medida: UnidadMedidaType
    cantidad_actual: Decimal = Field(default=Decimal("0"), ge=0)
    cantidad_minima: Decimal = Field(default=Decimal("0"), ge=0)
    cantidad_reorden: Decimal = Field(default=Decimal("0"), ge=0)
    costo_unitario: Decimal = Field(default=Decimal("0"), ge=0)

    @field_validator("nombre")
    @classmethod
    def nombre_no_vacio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El nombre del ingrediente no puede estar vacío.")
        return v

    @field_validator("cantidad_actual", "cantidad_minima", "cantidad_reorden", "costo_unitario")
    @classmethod
    def no_negativos(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Este campo no puede ser negativo.")
        return v


class IngredienteUpdate(BaseModel):
    """PUT — full replacement of mutable fields."""
    categoria_id: Optional[int] = None
    nombre: Optional[str] = Field(default=None, max_length=150)
    descripcion: Optional[str] = Field(default=None, max_length=500)
    unidad_medida: Optional[UnidadMedidaType] = None
    cantidad_minima: Optional[Decimal] = Field(default=None, ge=0)
    cantidad_reorden: Optional[Decimal] = Field(default=None, ge=0)
    costo_unitario: Optional[Decimal] = Field(default=None, ge=0)
    activo: Optional[bool] = None

    @field_validator("nombre")
    @classmethod
    def nombre_no_vacio(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("El nombre no puede estar vacío.")
        return v


class IngredienteResponse(BaseModel):
    id: int
    categoria_id: int
    nombre: str
    descripcion: Optional[str] = None
    unidad_medida: str
    cantidad_actual: Decimal
    cantidad_minima: Decimal
    cantidad_reorden: Decimal
    costo_unitario: Decimal
    activo: bool
    # Derived field: True when cantidad_actual <= cantidad_minima
    alerta_stock: bool
    ultima_modificacion: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_alert(cls, ingrediente) -> "IngredienteResponse":
        data = dict(
            id=ingrediente.id,
            categoria_id=ingrediente.categoria_id,
            nombre=ingrediente.nombre,
            descripcion=ingrediente.descripcion,
            unidad_medida=ingrediente.unidad_medida,
            cantidad_actual=ingrediente.cantidad_actual,
            cantidad_minima=ingrediente.cantidad_minima,
            cantidad_reorden=ingrediente.cantidad_reorden,
            costo_unitario=ingrediente.costo_unitario,
            activo=ingrediente.activo,
            alerta_stock=ingrediente.cantidad_actual <= ingrediente.cantidad_minima,
            ultima_modificacion=ingrediente.ultima_modificacion,
        )
        return cls(**data)


# =============================================================================
# RECETA / BOM
# =============================================================================

class ComponenteRecetaCreate(BaseModel):
    """A single BOM line: one ingredient + how much is needed per product unit."""
    ingrediente_id: int
    cantidad_requerida: Decimal = Field(..., gt=0,
                                        description="Cantidad requerida por unidad de producto (> 0)")
    unidad_medida: UnidadMedidaType = Field(
        ..., description="Unidad en que se expresa la cantidad en la receta"
    )


class ComponenteRecetaResponse(BaseModel):
    id: int
    ingrediente_id: int
    ingrediente_nombre: str
    cantidad_requerida: Decimal
    unidad_medida: str

    class Config:
        from_attributes = True


class RecetaProductoCreate(BaseModel):
    """
    Create or completely replace the recipe for a product.
    Existing components will be deleted and replaced with the new list.
    """
    producto_id: int
    descripcion: Optional[str] = Field(default=None, max_length=500)
    componentes: List[ComponenteRecetaCreate] = Field(
        ..., min_length=1, description="Al menos un componente es requerido"
    )

    @model_validator(mode="after")
    def no_ingredientes_duplicados(self) -> "RecetaProductoCreate":
        ids = [c.ingrediente_id for c in self.componentes]
        if len(ids) != len(set(ids)):
            raise ValueError("La receta no puede tener el mismo ingrediente más de una vez.")
        return self


class RecetaProductoResponse(BaseModel):
    id: int
    producto_id: int
    descripcion: Optional[str] = None
    activo: bool
    ultima_modificacion: datetime
    componentes: List[ComponenteRecetaResponse]

    class Config:
        from_attributes = True


# =============================================================================
# MOVIMIENTO INGREDIENTE
# =============================================================================

class MovimientoIngredienteCreate(BaseModel):
    """
    Request body for manual ingredient stock movements.
    Auto movements (CONSUMO_VENTA, DEVOLUCION) are system-only.

    For CORRECCION: *cantidad* is the new ABSOLUTE stock level.
    For all others: *cantidad* is the positive delta.
    """
    ingrediente_id: int
    tipo_movimiento: TipoMovimientoManual
    cantidad: Decimal = Field(..., ge=0,
                              description="Delta (>= 0). For CORRECCION: new absolute quantity.")
    notas: Optional[str] = Field(default=None, max_length=500)
    documento_referencia: Optional[str] = Field(default=None, max_length=100)
    movimiento_local_uuid: Optional[UUID] = Field(
        default=None,
        description="Client-side UUID for idempotency (duplicate requests are ignored)"
    )


class MovimientoIngredienteResponse(BaseModel):
    id: int
    ingrediente_id: int
    empleado_id: Optional[int] = None
    tipo_movimiento: str
    cantidad: Decimal
    cantidad_anterior: Decimal
    cantidad_nueva: Decimal
    documento_referencia: Optional[str] = None
    pedido_id: Optional[int] = None
    notas: Optional[str] = None
    fecha_movimiento: datetime
    movimiento_local_uuid: Optional[UUID] = None

    class Config:
        from_attributes = True


# =============================================================================
# DISPONIBILIDAD / REPORTING
# =============================================================================

class DisponibilidadProductoResponse(BaseModel):
    """Calculated product availability based on ingredient stock."""
    producto_id: int
    producto_nombre: str
    tipo_control_inventario: str
    # None = not tracked (NINGUNO) or not applicable (PRODUCTO uses InventarioActual)
    cantidad_producible: Optional[int] = None
    ingrediente_limitante: Optional[str] = None
    tiene_receta: bool


class AlertaIngredienteResponse(BaseModel):
    """Ingredient below its minimum stock threshold."""
    id: int
    nombre: str
    unidad_medida: str
    cantidad_actual: Decimal
    cantidad_minima: Decimal
    cantidad_reorden: Decimal
    # How much needs to be purchased to reach reorder level
    deficit: Decimal

    class Config:
        from_attributes = True
