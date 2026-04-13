from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from decimal import Decimal

from app.db.database import get_session
from app.models.core_models import PedidoGlobal, DetallePedido
from app.schemas.pedidos_schema import PedidoCreate, PedidoResponse, CancelarPedidoRequest, AgregarItemsRequest, ResumenCuentaResponse, ItemResumen, SolicitarCuentaRequest
from app.logic.orders_manager import OrdersManager
from app.logic.sales_manager import SalesManager

from pydantic import BaseModel


class FacturarPedidoRequest(BaseModel):
    empleado_id: int

router = APIRouter(
    prefix="/api/v1/pedidos",
    tags=["Módulo de Pedidos"]
)


@router.post("/", response_model=PedidoResponse)
def crear_pedido_completo(pedido_in: PedidoCreate, session: Session = Depends(get_session)):
    try:
        if pedido_in.factura_local_uuid:
            existente = session.exec(
                select(PedidoGlobal).where(PedidoGlobal.factura_local_uuid == pedido_in.factura_local_uuid)
            ).first()
            if existente:
                return existente

        nuevo_pedido = OrdersManager.crear_pedido_completo(
            session=session,
            canal_origen=pedido_in.canal_origen,
            cliente_id=pedido_in.cliente_id,
            empleado_id=pedido_in.empleado_id,
            items=[item.model_dump() for item in pedido_in.detalles],
            mesa=pedido_in.mesa,
            factura_local_uuid = pedido_in.factura_local_uuid,
            propina_extra=pedido_in.propina_extra
        )

        session.commit()
        session.refresh(nuevo_pedido)
        return nuevo_pedido

    except HTTPException as e:
        raise e
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=f"Error al procesar el pedido: {str(e)}")


@router.post("/{factura_local_uuid}/facturar", response_model=PedidoResponse)
def facturar_pedido(
        factura_local_uuid: str,
        payload: FacturarPedidoRequest, # ✅ Ahora FastAPI exige y entiende un JSON
        session: Session = Depends(get_session)
):
    try:
        # Buscamos el pedido usando el UUID
        pedido_global = session.exec(
            select(PedidoGlobal).where(PedidoGlobal.factura_local_uuid == factura_local_uuid)
        ).first()

        if not pedido_global:
            raise HTTPException(
                status_code=404,
                detail=f"Pedido con UUID {factura_local_uuid} no encontrado en el CORE."
            )

        # Pasamos el ID interno y sacamos el empleado_id del payload JSON
        resultado = SalesManager.facturar_pedido(
            session=session,
            pedido_id=pedido_global.id,
            empleado_caja_id=payload.empleado_id
        )

        session.commit()
        session.refresh(pedido_global)

        return pedido_global

    except HTTPException as e:
        raise e
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{identificador}/cancelar")
def cancelar_pedido(
    identificador: str,
    datos: CancelarPedidoRequest,
    session: Session = Depends(get_session)
):
    try:
        pedido = session.exec(
            select(PedidoGlobal).where(PedidoGlobal.factura_local_uuid == identificador)
        ).first()

        if not pedido:
            raise HTTPException(status_code=404, detail="Pedido no encontrado con ese UUID local.")

        resultado = SalesManager.cancelar_pedido(
            session=session,
            pedido_id=pedido.id,
            empleado_id=datos.empleado_id,
            motivo=datos.motivo
        )
        session.commit()
        return {"mensaje": "Cancelación procesada en el CORE", "pedido_id": pedido.id}

    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{id}", response_model=PedidoResponse)
def obtener_resumen(id: int, session: Session = Depends(get_session)):
    pedido = session.get(PedidoGlobal, id)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return pedido



@router.patch("/{factura_local_uuid}/agregar-items")
def agregar_items_a_pedido(
        factura_local_uuid: str,
        payload: AgregarItemsRequest,
        session: Session = Depends(get_session)
):
    """Suma nuevos productos a una cuenta que ya está abierta en una mesa."""
    try:
        # 1. Buscar el pedido cabecera
        pedido = session.exec(
            select(PedidoGlobal).where(PedidoGlobal.factura_local_uuid == factura_local_uuid)
        ).first()

        if not pedido:
            raise HTTPException(status_code=404, detail="Pedido no encontrado con ese UUID.")

        if pedido.estado in ["FACTURADO", "CANCELADO"]:
            raise HTTPException(status_code=400, detail="No se pueden agregar items a un pedido cerrado.")

        # 2. Actualizar totales de la cabecera
        pedido.subtotal += Decimal(str(payload.nuevo_subtotal_agregado))
        pedido.total_impuestos += Decimal(str(payload.nuevo_impuesto_agregado))
        pedido.propina_legal = pedido.subtotal * Decimal("0.10")
        pedido.total_general = pedido.subtotal + pedido.total_impuestos + pedido.propina_legal + pedido.propina_extra

        session.add(pedido)

        # 3. Insertar los nuevos detalles
        for item in payload.detalles_adicionales:
            nuevo_detalle = DetallePedido(
                pedido_id=pedido.id,
                producto_id=item.producto_id,
                cantidad=item.cantidad,
                # Corregimos los nombres según tu core_models.py:
                precio_unitario_historico=item.precio_unitario,
                impuesto_historico=Decimal("18.00"),  # O el valor que traigas del producto
                monto_impuesto=item.monto_impuesto,
                subtotal_linea=item.subtotal_linea,
                detalle_local_uuid=item.detalle_local_uuid
            )
            session.add(nuevo_detalle)

        session.commit()
        return {"mensaje": "Items añadidos exitosamente al CORE", "nuevo_total": pedido.total_general}

    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{factura_local_uuid}/resumen", response_model=ResumenCuentaResponse)
def resumen_cuenta_uuid(factura_local_uuid: str, session: Session = Depends(get_session)):
    """Devuelve el estado financiero y los items de la cuenta para mostrar en la App."""
    pedido = session.exec(
        select(PedidoGlobal).where(PedidoGlobal.factura_local_uuid == factura_local_uuid)
    ).first()

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    # Obtener los detalles. Ajusta esto si tu relación en SQLAlchemy se llama diferente
    detalles = session.exec(select(DetallePedido).where(DetallePedido.pedido_id == pedido.id)).all()

    # Mapeo básico para el resumen (Asumiendo que tienes una forma de obtener el nombre del producto)
    # Si no tienes join con Producto aquí, podrías devolver solo el producto_id por simplicidad.
    items_list = []
    for d in detalles:
        items_list.append(
            ItemResumen(
                producto_nombre=f"Producto {d.producto_id}",  # Idealmente hacer join con Producto
                cantidad=d.cantidad,
                subtotal_linea=d.subtotal_linea,
                estado_preparacion="ENTREGADO"
            )
        )

    return ResumenCuentaResponse(
        factura_local_uuid=pedido.factura_local_uuid,
        estado_cuenta=pedido.estado,
        subtotal_acumulado=pedido.subtotal,
        total_impuestos_acumulado=pedido.total_impuestos,
        propina_legal_acumulada=pedido.propina_legal,
        propina_extra_acumulada=pedido.propina_extra,
        total_general_acumulado=pedido.total_general,
        items_consumidos=items_list
    )


@router.post("/{factura_local_uuid}/solicitar-cuenta")
def solicitar_cuenta(
        factura_local_uuid: str,
        payload: SolicitarCuentaRequest,
        session: Session = Depends(get_session)
):
    """Cambia el estado para que la Caja sepa que debe ir a cobrar."""
    pedido = session.exec(
        select(PedidoGlobal).where(PedidoGlobal.factura_local_uuid == factura_local_uuid)
    ).first()

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado.")

    pedido.estado = "POR_FACTURAR"
    pedido.propina_extra = payload.propina_extra
    pedido.total_general = pedido.subtotal + pedido.total_impuestos + pedido.propina_legal + pedido.propina_extra

    session.add(pedido)
    session.commit()

    return {"mensaje": f"El mesero ha sido notificado para cobrar con {payload.metodo_pago_preferido}"}