"""
Sales Manager — order billing and cancellation with multi-modal inventory reversal.

On cancellation:
    INGREDIENTES products → reverse via IngredientInventoryManager (DEVOLUCION movements)
    PRODUCTO products     → reverse via legacy InventoryManager (ENTRADA movements)
    NINGUNO products      → no reversal needed
"""

from fastapi import HTTPException
from sqlmodel import Session, select

from app.logic.ingredient_inventory_manager import IngredientInventoryManager
from app.logic.inventory_manager import InventoryManager
from app.models.core_models import DetallePedido, PedidoGlobal, Producto


class SalesManager:

    @staticmethod
    def facturar_pedido(session: Session, pedido_id: int, empleado_caja_id: int) -> dict:
        """
        Mark an order as FACTURADO.
        Ingredient deductions already happened at order creation — no additional
        stock changes are needed here.
        """
        pedido = session.get(PedidoGlobal, pedido_id)
        if not pedido:
            raise HTTPException(
                status_code=404,
                detail=f"Pedido #{pedido_id} no encontrado en el CORE.",
            )

        if pedido.estado in ["FACTURADO", "CANCELADO"]:
            raise HTTPException(
                status_code=400,
                detail=f"Operación inválida. El pedido actualmente está en estado {pedido.estado}.",
            )

        pedido.estado = "FACTURADO"
        pedido.empleado_id = empleado_caja_id
        session.add(pedido)

        return {
            "mensaje": "Pedido facturado exitosamente",
            "pedido_id": pedido.id,
            "total_cobrado": pedido.total_general,
            "estado": pedido.estado,
        }

    @staticmethod
    def cancelar_pedido(
        session: Session,
        pedido_id: int,
        empleado_id: int,
        motivo: str,
    ) -> dict:
        """
        Cancel an order and reverse all stock deductions.

        Reversal strategy per product tipo_control_inventario:
          INGREDIENTES → IngredientInventoryManager.revertir_consumo_pedido
                         (finds CONSUMO_VENTA movements by pedido_id and reverses each)
          PRODUCTO     → InventoryManager.registrar_movimiento (ENTRADA per item)
          NINGUNO      → no reversal needed
        """
        pedido = session.get(PedidoGlobal, pedido_id)
        if not pedido:
            raise HTTPException(status_code=404, detail="Pedido no encontrado.")

        if pedido.estado == "CANCELADO":
            raise HTTPException(
                status_code=400, detail="El pedido ya fue cancelado previamente."
            )

        # ── Reverse ingredient-based stock (all CONSUMO_VENTA for this order) ──
        IngredientInventoryManager.revertir_consumo_pedido(
            session=session,
            pedido_id=pedido_id,
            empleado_id=empleado_id,
        )

        # ── Reverse legacy product-level stock for PRODUCTO-type products ─────
        detalles = session.exec(
            select(DetallePedido).where(DetallePedido.pedido_id == pedido_id)
        ).all()

        for item in detalles:
            producto = session.get(Producto, item.producto_id)
            if not producto:
                continue

            tipo_control = getattr(producto, "tipo_control_inventario", "PRODUCTO")

            if tipo_control == "PRODUCTO":
                InventoryManager.registrar_movimiento(
                    session=session,
                    producto_id=item.producto_id,
                    cantidad=item.cantidad,
                    tipo="ENTRADA",
                    motivo=(
                        f"Reversión por Cancelación Pedido #{pedido_id}. "
                        f"Motivo: {motivo}"
                    ),
                    empleado_id=empleado_id,
                    factura_local_uuid=pedido.factura_local_uuid,
                )
            # INGREDIENTES → already reversed above
            # NINGUNO      → no reversal needed

        pedido.estado = "CANCELADO"
        session.add(pedido)

        return {
            "mensaje": f"Pedido {pedido_id} cancelado.",
            "stock_reversado": True,
            "motivo": motivo,
        }