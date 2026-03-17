from sqlmodel import Session, select
from datetime import datetime
from fastapi import HTTPException
from app.models.core_models import InventarioActual, MovimientoInventario


class InventoryManager:
    @staticmethod
    def registrar_movimiento(session: Session, producto_id: int, cantidad: int, tipo: str, motivo: str,
                             empleado_id: int = None):
        stock = session.exec(select(InventarioActual).where(InventarioActual.producto_id == producto_id)).first()
        if not stock:
            raise HTTPException(status_code=404, detail="Producto no inicializado en inventario.")

        if tipo == 'SALIDA' and stock.cantidad_disponible < cantidad:
            raise HTTPException(status_code=400, detail=f"Stock insuficiente. Disponible: {stock.cantidad_disponible}")

        if tipo == 'ENTRADA':
            stock.cantidad_disponible += cantidad
        elif tipo == 'SALIDA':
            stock.cantidad_disponible -= cantidad
        elif tipo == 'AJUSTE':
            stock.cantidad_disponible = cantidad

        stock.ultima_modificacion = datetime.now()
        movimiento = MovimientoInventario(
            producto_id=producto_id,
            empleado_id=empleado_id,
            tipo_movimiento=tipo,
            cantidad=cantidad,
            motivo=motivo
        )

        session.add(stock)
        session.add(movimiento)