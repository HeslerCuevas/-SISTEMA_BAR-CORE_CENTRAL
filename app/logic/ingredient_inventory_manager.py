"""
Ingredient Inventory Manager — Core Business Logic.

Handles all ingredient stock operations:
    - Availability calculation (how many units of a product can be produced)
    - Manual stock movements (COMPRA, AJUSTE_MANUAL, DESPERDICIO, etc.)
    - Automatic consumption on order creation (CONSUMO_VENTA)
    - Automatic reversal on order cancellation (DEVOLUCION)

All deductions follow a "validate-all, then deduct-all" pattern to ensure
atomicity: if ANY ingredient has insufficient stock, NO deduction occurs.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from app.logic.unit_converter import UnitConversionError, convert
from app.models.core_models import (
    ComponenteReceta,
    Ingrediente,
    MovimientoIngrediente,
    Producto,
    RecetaProducto,
)

# Movement types that ADD stock
_TIPOS_ENTRADA = frozenset({"COMPRA", "AJUSTE_MANUAL", "CARGA_INICIAL", "DEVOLUCION"})

# Movement types that REMOVE stock
_TIPOS_SALIDA = frozenset({"CONSUMO_VENTA", "DESPERDICIO"})

# CORRECCION sets an absolute value — handled separately
_TIPO_CORRECCION = "CORRECCION"

# All movement types recognised by manual endpoints (excludes auto types)
TIPOS_MOVIMIENTO_MANUAL = frozenset(
    {"COMPRA", "AJUSTE_MANUAL", "DESPERDICIO", "CORRECCION", "CARGA_INICIAL"}
)

# All valid movement types
TIPOS_MOVIMIENTO_VALIDOS = frozenset(
    _TIPOS_ENTRADA | _TIPOS_SALIDA | {_TIPO_CORRECCION}
)




class IngredientInventoryManager:
    """
    Static-method manager that mirrors the pattern used by the legacy
    InventoryManager — no instance state, session always passed explicitly.
    """

    # ─── Availability calculation ─────────────────────────────────────────────

    @staticmethod
    def calcular_disponibilidad_producto(
        session: Session,
        producto_id: int,
    ) -> dict:
        """
        Calculate how many units of *producto_id* can be produced given the
        current ingredient stock.

        Returns a dict:
        {
            "cantidad_producible": int,
            "ingrediente_limitante": str | None,  # name of bottleneck ingredient
            "tiene_receta": bool,
        }

        Rules:
        - If no active recipe exists → {"cantidad_producible": None, "tiene_receta": False}
        - If an ingredient is inactive or missing → quantity = 0
        - If unit conversion fails → quantity = 0 with an error note
        - Result is floor(min(stock_i / need_i)) across all components
        """
        receta = session.exec(
            select(RecetaProducto).where(
                RecetaProducto.producto_id == producto_id,
                RecetaProducto.activo == True,
            )
        ).first()

        if not receta:
            return {
                "cantidad_producible": None,
                "ingrediente_limitante": None,
                "tiene_receta": False,
            }

        componentes: List[ComponenteReceta] = session.exec(
            select(ComponenteReceta).where(ComponenteReceta.receta_id == receta.id)
        ).all()

        if not componentes:
            # Recipe header exists but has no lines — treat as not configured
            return {
                "cantidad_producible": None,
                "ingrediente_limitante": None,
                "tiene_receta": True,
            }

        min_producible: Optional[int] = None
        ingrediente_limitante: Optional[str] = None

        for comp in componentes:
            ingrediente = session.get(Ingrediente, comp.ingrediente_id)

            if not ingrediente or not ingrediente.activo:
                return {
                    "cantidad_producible": 0,
                    "ingrediente_limitante": getattr(ingrediente, "nombre", f"id={comp.ingrediente_id}"),
                    "tiene_receta": True,
                }

            try:
                # Convert recipe unit → ingredient's canonical storage unit
                cantidad_requerida_convertida = convert(
                    comp.cantidad_requerida,
                    comp.unidad_medida,
                    ingrediente.unidad_medida,
                )
            except UnitConversionError:
                # Misconfigured recipe — report as 0 to surface the problem
                return {
                    "cantidad_producible": 0,
                    "ingrediente_limitante": ingrediente.nombre,
                    "tiene_receta": True,
                }

            if cantidad_requerida_convertida <= 0:
                continue

            producible = int(
                math.floor(float(ingrediente.cantidad_actual) / float(cantidad_requerida_convertida))
            )

            if min_producible is None or producible < min_producible:
                min_producible = producible
                ingrediente_limitante = ingrediente.nombre

        return {
            "cantidad_producible": min_producible if min_producible is not None else 0,
            "ingrediente_limitante": ingrediente_limitante,
            "tiene_receta": True,
        }

    # ─── Single ingredient movement ───────────────────────────────────────────

    @staticmethod
    def registrar_movimiento_ingrediente(
        session: Session,
        ingrediente_id: int,
        tipo: str,
        cantidad: Decimal,
        empleado_id: Optional[int] = None,
        notas: Optional[str] = None,
        pedido_id: Optional[int] = None,
        documento_referencia: Optional[str] = None,
        movimiento_local_uuid: Optional[str] = None,
    ) -> Ingrediente:
        """
        Record an ingredient stock movement and update the ingredient's current
        quantity.

        For CORRECCION: *cantidad* is the NEW ABSOLUTE stock level.
        For all others:  *cantidad* is the positive delta to add or remove.

        Idempotency: if *movimiento_local_uuid* was already processed, returns
        the ingredient unchanged (no duplicate movement).

        Raises HTTPException 400 / 404 on validation failures.
        """
        # ── Validate tipo ──────────────────────────────────────────────────
        if tipo not in TIPOS_MOVIMIENTO_VALIDOS:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Tipo de movimiento '{tipo}' inválido. "
                    f"Valores válidos: {sorted(TIPOS_MOVIMIENTO_VALIDOS)}"
                ),
            )

        if cantidad < 0:
            raise HTTPException(
                status_code=400,
                detail="La cantidad del movimiento no puede ser negativa.",
            )

        # ── Idempotency check ──────────────────────────────────────────────
        if movimiento_local_uuid:
            previo = session.exec(
                select(MovimientoIngrediente).where(
                    MovimientoIngrediente.movimiento_local_uuid == movimiento_local_uuid
                )
            ).first()
            if previo:
                return session.get(Ingrediente, ingrediente_id)

        # ── Load ingredient ────────────────────────────────────────────────
        ingrediente = session.get(Ingrediente, ingrediente_id)
        if not ingrediente:
            raise HTTPException(
                status_code=404,
                detail=f"Ingrediente id={ingrediente_id} no encontrado.",
            )
        if not ingrediente.activo:
            raise HTTPException(
                status_code=400,
                detail=f"El ingrediente '{ingrediente.nombre}' está inactivo y no puede recibir movimientos.",
            )

        cantidad_anterior = Decimal(str(ingrediente.cantidad_actual))

        # ── Calculate new quantity ─────────────────────────────────────────
        if tipo == _TIPO_CORRECCION:
            # cantidad = absolute target value
            cantidad_nueva = Decimal(str(cantidad))
            cantidad_registrada = cantidad  # stored as-is for auditability
        elif tipo in _TIPOS_ENTRADA:
            cantidad_nueva = cantidad_anterior + Decimal(str(cantidad))
            cantidad_registrada = cantidad
        else:  # _TIPOS_SALIDA
            cantidad_registrada = Decimal(str(cantidad))
            if cantidad_anterior < cantidad_registrada:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Stock insuficiente de '{ingrediente.nombre}'. "
                        f"Disponible: {float(cantidad_anterior):.4f} {ingrediente.unidad_medida}, "
                        f"Requerido: {float(cantidad_registrada):.4f} {ingrediente.unidad_medida}."
                    ),
                )
            cantidad_nueva = cantidad_anterior - cantidad_registrada

        # Final guard — quantity must never go below 0
        if cantidad_nueva < 0:
            raise HTTPException(
                status_code=400,
                detail=f"El resultado de este movimiento dejaría el stock de '{ingrediente.nombre}' en negativo.",
            )

        # ── Persist ────────────────────────────────────────────────────────
        ingrediente.cantidad_actual = cantidad_nueva
        ingrediente.ultima_modificacion = datetime.now(timezone.utc)

        movimiento = MovimientoIngrediente(
            ingrediente_id=ingrediente_id,
            empleado_id=empleado_id,
            tipo_movimiento=tipo,
            cantidad=cantidad_registrada,
            cantidad_anterior=cantidad_anterior,
            cantidad_nueva=cantidad_nueva,
            documento_referencia=documento_referencia,
            pedido_id=pedido_id,
            notas=notas,
            movimiento_local_uuid=movimiento_local_uuid,
        )

        session.add(ingrediente)
        session.add(movimiento)

        return ingrediente

    # ─── Batch consumption on order creation ──────────────────────────────────

    @staticmethod
    def consumir_ingredientes_pedido(
        session: Session,
        pedido_id: int,
        detalles: List[dict],
        empleado_id: Optional[int],
        factura_uuid=None,
    ) -> None:
        """
        Consume ingredients for all items in an order atomically.

        Algorithm:
            1. Build the full deduction map {ingrediente_id: Decimal total_needed}
               by iterating every item's recipe and converting units.
            2. Validate EVERY ingredient has enough stock.
            3. Only THEN deduct all — no partial deductions on failure.

        *detalles* is a list of {"producto_id": int, "cantidad": int} for
        products with tipo_control_inventario == 'INGREDIENTES'.

        Raises HTTPException 400 if any ingredient has insufficient stock.
        """
        # Step 1: aggregate total consumption per ingredient
        totales: dict[int, dict] = defaultdict(lambda: {"cantidad": Decimal("0"), "nombre": "", "unidad": ""})

        for item in detalles:
            producto = session.get(Producto, item["producto_id"])
            if not producto:
                continue

            receta = session.exec(
                select(RecetaProducto).where(
                    RecetaProducto.producto_id == item["producto_id"],
                    RecetaProducto.activo == True,
                )
            ).first()

            if not receta:
                # No recipe configured — skip
                continue

            componentes: List[ComponenteReceta] = session.exec(
                select(ComponenteReceta).where(ComponenteReceta.receta_id == receta.id)
            ).all()

            for comp in componentes:
                ingrediente = session.get(Ingrediente, comp.ingrediente_id)
                if not ingrediente:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Ingrediente id={comp.ingrediente_id} referenciado en la receta del producto "
                               f"'{producto.nombre}' no existe.",
                    )
                if not ingrediente.activo:
                    raise HTTPException(
                        status_code=400,
                        detail=f"El ingrediente '{ingrediente.nombre}' está inactivo. "
                               f"Actualiza la receta del producto '{producto.nombre}'.",
                    )

                try:
                    # Convert recipe unit → ingredient's canonical storage unit
                    cantidad_por_unidad = convert(
                        comp.cantidad_requerida,
                        comp.unidad_medida,
                        ingrediente.unidad_medida,
                    )
                except UnitConversionError as exc:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Error de conversión de unidades en receta del producto "
                               f"'{producto.nombre}': {exc}",
                    )

                cantidad_total = cantidad_por_unidad * Decimal(str(item["cantidad"]))
                totales[ingrediente.id]["cantidad"] += cantidad_total
                totales[ingrediente.id]["nombre"] = ingrediente.nombre
                totales[ingrediente.id]["unidad"] = ingrediente.unidad_medida

        if not totales:
            return  # Nothing to consume (no recipes found)

        # Step 2: validate ALL before touching anything
        for ing_id, info in totales.items():
            ingrediente = session.get(Ingrediente, ing_id)
            if ingrediente.cantidad_actual < info["cantidad"]:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Stock insuficiente de '{info['nombre']}'. "
                        f"Disponible: {float(ingrediente.cantidad_actual):.4f} {info['unidad']}, "
                        f"Requerido: {float(info['cantidad']):.4f} {info['unidad']}. "
                        f"No se puede crear el pedido."
                    ),
                )

        # Step 3: deduct all
        for ing_id, info in totales.items():
            IngredientInventoryManager.registrar_movimiento_ingrediente(
                session=session,
                ingrediente_id=ing_id,
                tipo="CONSUMO_VENTA",
                cantidad=info["cantidad"],
                empleado_id=empleado_id,
                pedido_id=pedido_id,
                notas=f"Consumo automático por creación de pedido #{pedido_id}",
                documento_referencia=str(factura_uuid) if factura_uuid else None,
            )

    # ─── Reversal on order cancellation ──────────────────────────────────────

    @staticmethod
    def revertir_consumo_pedido(
        session: Session,
        pedido_id: int,
        empleado_id: Optional[int],
    ) -> None:
        """
        Reverse all CONSUMO_VENTA movements associated with *pedido_id*.
        Creates a corresponding DEVOLUCION movement for each.
        """
        movimientos: List[MovimientoIngrediente] = session.exec(
            select(MovimientoIngrediente).where(
                MovimientoIngrediente.pedido_id == pedido_id,
                MovimientoIngrediente.tipo_movimiento == "CONSUMO_VENTA",
            )
        ).all()

        for mov in movimientos:
            IngredientInventoryManager.registrar_movimiento_ingrediente(
                session=session,
                ingrediente_id=mov.ingrediente_id,
                tipo="DEVOLUCION",
                cantidad=mov.cantidad,
                empleado_id=empleado_id,
                pedido_id=pedido_id,
                notas=f"Reversión automática por cancelación de pedido #{pedido_id}",
                documento_referencia=mov.documento_referencia,
            )
