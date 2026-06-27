"""
Orders Manager — order creation with multi-modal inventory control.

Routing logic per product's tipo_control_inventario:
    INGREDIENTES → batch ingredient consumption via IngredientInventoryManager
    PRODUCTO     → legacy per-unit deduction via InventoryManager
    NINGUNO      → no stock operations (service charges, combos, etc.)

The ingredient path uses a "validate-all, then deduct-all" pattern:
all items are collected first; stock is only deducted after validation passes
for every ingredient. This prevents partial deductions on failure.
"""

from decimal import Decimal
from typing import Optional
import uuid

from fastapi import HTTPException
from sqlmodel import Session

from app.logic.ingredient_inventory_manager import IngredientInventoryManager
from app.logic.inventory_manager import InventoryManager
from app.models.core_models import DetallePedido, PedidoGlobal, Producto


class OrdersManager:

    @staticmethod
    def crear_pedido_completo(
        session: Session,
        canal_origen: str,
        cliente_id: Optional[int],
        empleado_id: Optional[int],
        items: list[dict],
        mesa: Optional[int] = None,
        factura_local_uuid: Optional[uuid.UUID] = None,
        propina_extra: Decimal = Decimal("0.0"),
    ) -> PedidoGlobal:
        """
        Create a complete order with all its line items and handle inventory
        deductions according to each product's inventory control type.

        Steps:
        1. Create order header and flush to get the ID.
        2. Iterate items: create line items and route to the correct stock path.
        3. Process ingredient-based items in a single batch (atomic validate + deduct).
        4. Finalize order totals.
        """
        nuevo_pedido = PedidoGlobal(
            cliente_id=cliente_id,
            empleado_id=empleado_id,
            canal_origen=canal_origen,
            mesa=mesa,
            estado="PENDIENTE",
            factura_local_uuid=factura_local_uuid,
            propina_extra=propina_extra,
        )
        session.add(nuevo_pedido)
        session.flush()  # Obtain nuevo_pedido.id for FK references

        subtotal_global = Decimal("0.0")
        impuestos_global = Decimal("0.0")

        # Collect ingredient-type items for batch processing
        items_ingrediente: list[dict] = []

        for item in items:
            producto = session.get(Producto, item["producto_id"])
            if not producto or not producto.activo:
                raise HTTPException(
                    status_code=404,
                    detail=f"Producto id={item['producto_id']} no encontrado o está inactivo.",
                )

            # Load tax rate (lazy-loaded relationship)
            tasa = (
                Decimal(str(producto.impuesto.tasa_porcentaje))
                if producto.impuesto
                else Decimal("0.0")
            )

            subtotal_linea = Decimal(str(producto.precio_base)) * item["cantidad"]
            monto_impuesto_linea = subtotal_linea * (tasa / 100)

            detalle = DetallePedido(
                pedido_id=nuevo_pedido.id,
                producto_id=producto.id,
                cantidad=item["cantidad"],
                precio_unitario_historico=producto.precio_base,
                impuesto_historico=tasa,
                monto_impuesto=monto_impuesto_linea,
                subtotal_linea=subtotal_linea,
                detalle_local_uuid=item.get("detalle_local_uuid"),
            )
            session.add(detalle)

            subtotal_global += subtotal_linea
            impuestos_global += monto_impuesto_linea

            # ── Route stock operation based on inventory control type ──────
            tipo_control = getattr(producto, "tipo_control_inventario", "PRODUCTO")

            if tipo_control == "INGREDIENTES":
                # Defer to batch processor (validates all before touching anything)
                items_ingrediente.append(
                    {"producto_id": producto.id, "cantidad": item["cantidad"]}
                )

            elif tipo_control == "PRODUCTO":
                # Legacy: deduct product-level stock immediately per item
                InventoryManager.registrar_movimiento(
                    session=session,
                    producto_id=producto.id,
                    cantidad=item["cantidad"],
                    tipo="SALIDA",
                    motivo=f"Venta canal {canal_origen} - Pedido #{nuevo_pedido.id}",
                    empleado_id=empleado_id,
                    movimiento_local_uuid=item.get("detalle_local_uuid"),
                    factura_local_uuid=factura_local_uuid,
                )

            # NINGUNO → no stock operations (intentionally skipped)

        # ── Batch ingredient consumption (atomic: all validated before any deduction) ──
        if items_ingrediente:
            IngredientInventoryManager.consumir_ingredientes_pedido(
                session=session,
                pedido_id=nuevo_pedido.id,
                detalles=items_ingrediente,
                empleado_id=empleado_id,
                factura_uuid=factura_local_uuid,
            )

        # ── Finalize totals ───────────────────────────────────────────────────
        propina = subtotal_global * Decimal("0.10")

        nuevo_pedido.subtotal = subtotal_global
        nuevo_pedido.total_impuestos = impuestos_global
        nuevo_pedido.propina_legal = propina
        nuevo_pedido.total_general = subtotal_global + impuestos_global + propina + propina_extra

        return nuevo_pedido