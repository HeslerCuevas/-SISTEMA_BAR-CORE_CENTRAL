from sqlmodel import Session
from fastapi import HTTPException
from app.models.core_models import PedidoGlobal, DetallePedido, Producto, Impuesto
from app.logic.inventory_manager import InventoryManager

class OrdersManager:
    @staticmethod
    def crear_pedido_completo(session: Session, canal_origen: str, cliente_id: int, empleado_id: int, items: list[dict]):
        """
        Lógica Core: Orquesta la creación de un pedido evaluando stock, precios e impuestos.
        items = [{"producto_id": 1, "cantidad": 2}, ...]
        """
        nuevo_pedido = PedidoGlobal(
            cliente_id=cliente_id,
            empleado_id=empleado_id,
            canal_origen=canal_origen,
            estado="PENDIENTE"
        )
        session.add(nuevo_pedido)
        session.flush()

        subtotal_global = 0.0
        impuestos_global = 0.0

        for item in items:
            producto = session.get(Producto, item["producto_id"])
            if not producto or not producto.activo:
                raise HTTPException(status_code=404, detail=f"Producto {item['producto_id']} no válido.")

            impuesto_db = session.get(Impuesto, producto.impuesto_id)
            tasa = impuesto_db.tasa_porcentaje if impuesto_db else 0.0

            subtotal_linea = float(producto.precio_base) * item["cantidad"]
            monto_impuesto_linea = subtotal_linea * (float(tasa) / 100)

            detalle = DetallePedido(
                pedido_id=nuevo_pedido.id,
                producto_id=producto.id,
                cantidad=item["cantidad"],
                precio_unitario_historico=producto.precio_base,
                impuesto_historico=tasa,
                monto_impuesto=monto_impuesto_linea,
                subtotal_linea=subtotal_linea
            )
            session.add(detalle)

            subtotal_global += subtotal_linea
            impuestos_global += monto_impuesto_linea

            InventoryManager.registrar_movimiento(
                session=session,
                producto_id=producto.id,
                cantidad=item["cantidad"],
                tipo="SALIDA",
                motivo=f"Venta desde canal {canal_origen}",
                empleado_id=empleado_id
            )

        nuevo_pedido.subtotal = subtotal_global
        nuevo_pedido.total_impuestos = impuestos_global
        nuevo_pedido.total_general = subtotal_global + impuestos_global

        return nuevo_pedido