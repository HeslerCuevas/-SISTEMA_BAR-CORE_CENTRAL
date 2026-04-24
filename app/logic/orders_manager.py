from sqlmodel import Session
from decimal import Decimal
from fastapi import HTTPException
from app.models.core_models import PedidoGlobal, DetallePedido, Producto
from app.logic.inventory_manager import InventoryManager
import uuid

class OrdersManager:
    @staticmethod
    def crear_pedido_completo(session: Session, canal_origen: str, cliente_id: int, empleado_id: int, items: list[dict],
                              mesa: int = None, factura_local_uuid: uuid.UUID = None, propina_extra: Decimal = Decimal("0.0")):
        nuevo_pedido = PedidoGlobal(
            cliente_id=cliente_id,
            empleado_id=empleado_id,
            canal_origen=canal_origen,
            mesa=mesa,
            estado="PENDIENTE",
            factura_local_uuid=factura_local_uuid,
            propina_extra=propina_extra
        )
        session.add(nuevo_pedido)
        session.flush()

        subtotal_global = Decimal("0.0")
        impuestos_global = Decimal("0.0")

        for item in items:
            producto = session.get(Producto, item["producto_id"])
            if not producto or not producto.activo:
                raise HTTPException(status_code=404, detail=f"Producto {item['producto_id']} no válido.")

            tasa = Decimal(str(producto.impuesto.tasa_porcentaje)) if producto.impuesto else Decimal("0.0")

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
                detalle_local_uuid=item.get("detalle_local_uuid")
            )
            session.add(detalle)

            subtotal_global += subtotal_linea
            impuestos_global += monto_impuesto_linea

            if producto.es_inventariable:
                InventoryManager.registrar_movimiento(
                    session=session,
                    producto_id=producto.id,
                    cantidad=item["cantidad"],
                    tipo="SALIDA",
                    motivo=f"Venta canal {canal_origen} - Pedido #{nuevo_pedido.id}",
                    empleado_id=empleado_id,
                    movimiento_local_uuid=item.get("detalle_local_uuid"),
                    factura_local_uuid=factura_local_uuid
                )

        propina = subtotal_global * Decimal("0.10")

        nuevo_pedido.subtotal = subtotal_global
        nuevo_pedido.total_impuestos = impuestos_global
        nuevo_pedido.propina_legal = propina
        nuevo_pedido.total_general = subtotal_global + impuestos_global + propina + propina_extra

        return nuevo_pedido