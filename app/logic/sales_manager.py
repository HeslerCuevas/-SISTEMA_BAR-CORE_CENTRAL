from sqlmodel import Session, select
from fastapi import HTTPException
from app.models.core_models import PedidoGlobal, DetallePedido, Producto
from app.logic.inventory_manager import InventoryManager


class SalesManager:

    @staticmethod
    def facturar_pedido(session: Session, pedido_id: int, empleado_caja_id: int):
        pedido = session.get(PedidoGlobal, pedido_id)
        if not pedido:
            raise HTTPException(status_code=404, detail=f"Pedido #{pedido_id} no encontrado en el CORE.")

        if pedido.estado in ['FACTURADO', 'CANCELADO']:
            raise HTTPException(
                status_code=400,
                detail=f"Operación inválida. El pedido actualmente está {pedido.estado}."
            )

        pedido.estado = "FACTURADO"
        pedido.empleado_id = empleado_caja_id

        session.add(pedido)

        return {
            "mensaje": "Pedido facturado exitosamente",
            "pedido_id": pedido.id,
            "total_cobrado": pedido.total_general,
            "estado": pedido.estado
        }

    @staticmethod
    def cancelar_pedido(session: Session, pedido_id: int, empleado_id: int, motivo: str):
        pedido = session.get(PedidoGlobal, pedido_id)
        if not pedido:
            raise HTTPException(status_code=404, detail="Pedido no encontrado.")

        if pedido.estado == 'CANCELADO':
            raise HTTPException(status_code=400, detail="El pedido ya fue cancelado previamente.")

        statement = select(DetallePedido).where(DetallePedido.pedido_id == pedido_id)
        detalles = session.exec(statement).all()

        for item in detalles:
            producto = session.get(Producto, item.producto_id)

            if producto and producto.es_inventariable:
                InventoryManager.registrar_movimiento(
                    session=session,
                    producto_id=item.producto_id,
                    cantidad=item.cantidad,
                    tipo="ENTRADA",
                    motivo=f"Reversión por Cancelación Pedido #{pedido_id}. Motivo: {motivo}",
                    empleado_id=empleado_id,
                    factura_local_uuid=pedido.factura_local_uuid
                )

        pedido.estado = "CANCELADO"
        session.add(pedido)

        return {
            "mensaje": f"Pedido {pedido_id} cancelado.",
            "stock_reversado": True,
            "motivo": motivo
        }