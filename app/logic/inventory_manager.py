from sqlmodel import Session, select
from datetime import datetime, timezone
import uuid
from fastapi import HTTPException
from app.models.core_models import InventarioActual, MovimientoInventario


class InventoryManager:
    @staticmethod
    def registrar_movimiento(
            session: Session,
            producto_id: int,
            cantidad: int,
            tipo: str,
            motivo: str,
            empleado_id: int = None,
            movimiento_local_uuid: str = None,
            factura_local_uuid: uuid.UUID = None
    ) -> InventarioActual:

        if cantidad < 0:
            raise HTTPException(status_code=400, detail="La cantidad del movimiento no puede ser negativa.")

        if movimiento_local_uuid:
            movimiento_previo = session.exec(
                select(MovimientoInventario).where(MovimientoInventario.movimiento_local_uuid == movimiento_local_uuid)
            ).first()
            if movimiento_previo:
                return session.exec(select(InventarioActual).where(InventarioActual.producto_id == producto_id)).first()

        stock = session.exec(select(InventarioActual).where(InventarioActual.producto_id == producto_id)).first()
        if not stock:
            stock = InventarioActual(
                producto_id=producto_id,
                cantidad_disponible=0,
                stock_minimo=5
            )
            session.add(stock)
            session.flush()

        if tipo == 'SALIDA' and stock.cantidad_disponible < cantidad:
            raise HTTPException(status_code=400, detail=f"Stock insuficiente. Disponible: {stock.cantidad_disponible}")

        cantidad_a_registrar = cantidad

        if tipo == 'ENTRADA':
            stock.cantidad_disponible += cantidad
        elif tipo == 'SALIDA':
            stock.cantidad_disponible -= cantidad
        elif tipo == 'AJUSTE':
            cantidad_a_registrar = cantidad - stock.cantidad_disponible
            stock.cantidad_disponible = cantidad

        stock.ultima_modificacion = datetime.now(timezone.utc)

        movimiento = MovimientoInventario(
            producto_id=producto_id,
            empleado_id=empleado_id,
            tipo_movimiento=tipo,
            cantidad=cantidad_a_registrar,
            motivo=motivo,
            movimiento_local_uuid=movimiento_local_uuid,
            factura_local_uuid=factura_local_uuid
        )

        session.add(stock)
        session.add(movimiento)

        return stock