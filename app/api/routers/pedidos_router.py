from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db.database import get_session
from app.models.core_models import PedidoGlobal, DetallePedido, Producto, Impuesto, InventarioActual, MovimientoInventario
from app.schemas.pedidos_schema import PedidoCreate, PedidoResponse, DetallePedidoCreate, DetallePedidoResponse

router = APIRouter(
    prefix="/api/v1/pedidos",
    tags=["Módulo de Pedidos"]
)

@router.post("/", response_model=PedidoResponse, tags=["Pedidos"])
def crear_pedido(pedido: PedidoCreate, session: Session = Depends(get_session)):
    try:
        if pedido.factura_local_uuid:
            pedido_existente = session.exec(
                select(PedidoGlobal).where(PedidoGlobal.factura_local_uuid == pedido.factura_local_uuid)
            ).first()
            if pedido_existente:
                return pedido_existente

        nuevo_pedido = PedidoGlobal(**pedido.model_dump())
        session.add(nuevo_pedido)
        session.commit()
        session.refresh(nuevo_pedido)

        return nuevo_pedido
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=f"Error al crear el pedido: {str(e)}")


@router.post("/{id}/items", response_model=DetallePedidoResponse, tags=["Pedidos"])
def agregar_item(id: int, item_in: DetallePedidoCreate, session: Session = Depends(get_session)):
    pedido_db = session.get(PedidoGlobal, id)
    if not pedido_db:
        raise HTTPException(status_code=404, detail="El pedido no existe.")

    producto_db = session.get(Producto, item_in.producto_id)
    if not producto_db:
        raise HTTPException(status_code=404, detail="El producto no encontrado.")

    try:
        impuesto = session.get(Impuesto, producto_db.impuesto_id)
        tasa = impuesto.tasa_porcentaje

        precio_base = producto_db.precio_base
        bruto_linea = precio_base * item_in.cantidad
        monto_impuesto_linea = bruto_linea * (tasa / 100)
        total_linea = bruto_linea + monto_impuesto_linea

        nuevo_item = DetallePedido(
            pedido_id=id,
            producto_id=item_in.producto_id,
            cantidad=item_in.cantidad,
            precio_unitario_historico=precio_base,
            impuesto_historico=tasa,
            monto_impuesto=monto_impuesto_linea,
            subtotal_linea=bruto_linea,
            detalle_local_uuid = item_in.detalle_local_uuid
        )
        session.add(nuevo_item)

        pedido_db.subtotal += bruto_linea
        pedido_db.total_impuestos += monto_impuesto_linea
        pedido_db.total_general += total_linea

        session.add(pedido_db)
        session.commit()
        session.refresh(nuevo_item)

        return nuevo_item

    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=f"Error al agregar el item al pedido: {str(e)}")


@router.get("/{id}", response_model=PedidoResponse)
def resumen_pedido(id: int, session: Session = Depends(get_session)):
    pedido = session.get(PedidoGlobal, id)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return pedido

@router.post("/{id}/facturar", response_model=PedidoResponse, tags=["Pedidos"])
def facturar(id: int, session: Session = Depends(get_session)):
    pedido = session.get(PedidoGlobal, id)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    if pedido.estado != "PENDIENTE":
        raise HTTPException(status_code=400, detail=f"El pedido no esta pendiente. Se encuentra {pedido.estado}")

    try:
        from decimal import Decimal
        if pedido.canal_origen == "CAJA" and pedido.mesa is not None:
            propina = pedido.subtotal * Decimal("0.10")
            pedido.propina_legal = round(propina, 2)
            pedido.total_general += pedido.propina_legal
        else:
            pedido.propina_legal = 0

        pedido.estado = "FACTURADO"

        session.add(pedido)

        descontar_inventario(id, session)

        session.commit()
        session.refresh(pedido)

        return pedido
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=f"Error al facturar: {str(e)}")


def descontar_inventario(pedido_id: int, session: Session):
    detalles = session.exec(select(DetallePedido).where(DetallePedido.pedido_id == pedido_id)).all()

    for item in detalles:
        producto = session.get(Producto, item.producto_id)

        if producto and producto.es_inventariable:
            inventario_db = session.exec(
                select(InventarioActual).where(InventarioActual.producto_id == item.producto_id)
            ).first()

            if inventario_db:
                if inventario_db.cantidad_disponible >= item.cantidad:
                    inventario_db.cantidad_disponible -= item.cantidad

                    # --- CAMBIO AQUÍ: Sello de tiempo para la Caja ---
                    inventario_db.ultima_modificacion = datetime.now()
                    # ------------------------------------------------

                    movimiento = MovimientoInventario(
                        producto_id=item.producto_id,
                        cantidad=item.cantidad,
                        tipo_movimiento="SALIDA",
                        motivo=f"Venta Pedido #{pedido_id}"
                    )
                    session.add(movimiento)
                    session.add(inventario_db)
                else:
                    raise HTTPException(status_code=400, detail=f"Stock insuficiente para {producto.nombre}")

