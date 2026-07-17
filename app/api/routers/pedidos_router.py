import uuid

from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.security import HTTPAuthorizationCredentials
from sqlmodel import Session, select
from decimal import Decimal
import json
from typing import List, Optional
import os

from app.db.database import get_session
from app.models.core_models import (
    PedidoGlobal, DetallePedido, Producto, ModificadorItem, DivisionCuenta
)
from app.schemas.pedidos_schema import (
    PedidoCreate, PedidoResponse, CancelarPedidoRequest, AgregarItemsRequest,
    ResumenCuentaResponse, ItemResumen, SolicitarCuentaRequest, ModificadorItemResponse,
    ModificadorItemRequest, FacturarPedidoRequest, SplitBillRequest, SplitBillResponse
)
from app.logic.orders_manager import OrdersManager
from app.logic.sales_manager import SalesManager
from app.services.audit_service import log_auditoria

from app.core.security import verificar_rol_empleado, security_bearer




router = APIRouter(
    prefix="/api/v1/pedidos",
    tags=["Módulo de Pedidos"]
)


@router.post("/", response_model=PedidoResponse)
def crear_pedido_completo(
        pedido_in: PedidoCreate,
        session: Session = Depends(get_session),
        token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
        x_gateway_token: Optional[str] = Header(None)
):
    gateway_secret = os.getenv("CORE_SECRET_KEY")
    is_gateway = x_gateway_token and gateway_secret and x_gateway_token == gateway_secret

    if not is_gateway:
        empleado_info = verificar_rol_empleado(
            token_obj.credentials,
            ["ADMIN", "GERENTE", "CAJERO"],
            session
        )

    try:
        if pedido_in.factura_local_uuid:
            existente = session.exec(
                select(PedidoGlobal).where(PedidoGlobal.factura_local_uuid == pedido_in.factura_local_uuid)
            ).first()
            if existente:
                return existente

        if pedido_in.mesa is not None:
            pedido_activo_en_mesa = session.exec(
                select(PedidoGlobal).where(
                    PedidoGlobal.mesa == str(pedido_in.mesa),
                    PedidoGlobal.estado.in_(["PENDIENTE", "ABIERTA", "EN_PREPARACION"])
                )
            ).first()
            if pedido_activo_en_mesa:
                raise HTTPException(
                    status_code=409,
                    detail=f"La mesa {pedido_in.mesa} ya está ocupada por un pedido activo."
                )

        nuevo_pedido = OrdersManager.crear_pedido_completo(
            session=session,
            canal_origen=pedido_in.canal_origen,
            cliente_id=pedido_in.cliente_id,
            empleado_id=pedido_in.empleado_id,
            items=[item.model_dump() for item in pedido_in.detalles],
            mesa=pedido_in.mesa,
            factura_local_uuid=pedido_in.factura_local_uuid,
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
    payload: FacturarPedidoRequest,
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    x_gateway_token: Optional[str] = Header(None)
):
    gateway_secret = os.getenv("CORE_SECRET_KEY")
    is_gateway = x_gateway_token and gateway_secret and x_gateway_token == gateway_secret

    if not is_gateway:
        empleado_info = verificar_rol_empleado(
            token_obj.credentials,
            ["ADMIN", "GERENTE", "CAJERO"],
            session
        )

    try:
        pedido_global = session.exec(
            select(PedidoGlobal).where(PedidoGlobal.factura_local_uuid == factura_local_uuid)
        ).first()

        if not pedido_global:
            raise HTTPException(
                status_code=404,
                detail=f"Pedido con UUID {factura_local_uuid} no encontrado en el CORE."
            )

        SalesManager.facturar_pedido(
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
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    x_gateway_token: Optional[str] = Header(None)
):
    gateway_secret = os.getenv("CORE_SECRET_KEY")
    is_gateway = x_gateway_token and gateway_secret and x_gateway_token == gateway_secret

    if not is_gateway:
        verificar_rol_empleado(token_obj.credentials, ["ADMIN", "GERENTE", "CAJERO"], session)

    try:
        pedido = session.exec(
            select(PedidoGlobal).where(PedidoGlobal.factura_local_uuid == identificador)
        ).first()

        if not pedido:
            raise HTTPException(status_code=404, detail="Pedido no encontrado con ese UUID local.")

        SalesManager.cancelar_pedido(
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


@router.patch("/{factura_local_uuid}/agregar-items")
def agregar_items_a_pedido(
    factura_local_uuid: str,
    payload: AgregarItemsRequest,
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    x_gateway_token: Optional[str] = Header(None)
):
    gateway_secret = os.getenv("CORE_SECRET_KEY")
    is_gateway = x_gateway_token and gateway_secret and x_gateway_token == gateway_secret

    if not is_gateway:
        verificar_rol_empleado(token_obj.credentials, ["ADMIN", "GERENTE", "CAJERO"], session)

    try:
        pedido = session.exec(
            select(PedidoGlobal).where(PedidoGlobal.factura_local_uuid == factura_local_uuid)
        ).first()

        if not pedido:
            raise HTTPException(status_code=404, detail="Pedido no encontrado con ese UUID.")

        if pedido.estado in ["FACTURADO", "CANCELADO"]:
            raise HTTPException(status_code=400, detail="No se pueden agregar items a un pedido cerrado.")

        pedido.subtotal += Decimal(str(payload.nuevo_subtotal_agregado))
        pedido.total_impuestos += Decimal(str(payload.nuevo_impuesto_agregado))
        pedido.propina_legal = pedido.subtotal * Decimal("0.10")
        pedido.total_general = pedido.subtotal + pedido.total_impuestos + pedido.propina_legal + pedido.propina_extra

        session.add(pedido)

        for item in payload.detalles_adicionales:
            nuevo_detalle = DetallePedido(
                pedido_id=pedido.id,
                producto_id=item.producto_id,
                cantidad=item.cantidad,
                precio_unitario_historico=item.precio_unitario,
                impuesto_historico=Decimal("18.00"),
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
    pedido = session.exec(
        select(PedidoGlobal).where(PedidoGlobal.factura_local_uuid == factura_local_uuid)
    ).first()

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    statement = (
        select(DetallePedido, Producto)
        .join(Producto, DetallePedido.producto_id == Producto.id)
        .where(DetallePedido.pedido_id == pedido.id)
    )
    resultados = session.exec(statement).all()

    items_list = []
    for detalle, producto in resultados:
        items_list.append(
            ItemResumen(
                producto_nombre=producto.nombre,
                cantidad=detalle.cantidad,
                subtotal_linea=detalle.subtotal_linea,
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


@router.get("/{factura_local_uuid}", response_model=PedidoResponse)
def obtener_pedido_por_uuid(factura_local_uuid: str, session: Session = Depends(get_session)):
    pedido = session.exec(
        select(PedidoGlobal).where(PedidoGlobal.factura_local_uuid == factura_local_uuid)
    ).first()

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado con ese UUID")

    return pedido


@router.post("/{factura_local_uuid}/solicitar-cuenta")
def solicitar_cuenta(
    factura_local_uuid: str,
    payload: SolicitarCuentaRequest,
    session: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):

    verificar_rol_empleado(token_obj.credentials, ["ADMIN", "GERENTE", "CAJERO"], session)

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


@router.post(
    "/{factura_local_uuid}/detalles/{detalle_pedido_uuid}/modificadores",
    response_model=ModificadorItemResponse,
    status_code=201
)
def agregar_modificador_item(
        factura_local_uuid: str,
        detalle_pedido_uuid: uuid.UUID,
        payload: ModificadorItemRequest,
        session: Session = Depends(get_session),
        token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):

    empleado_info = verificar_rol_empleado(
        token_obj.credentials,
        ["ADMIN", "GERENTE", "CAJERO"],
        session
    )

    pedido = session.exec(
        select(PedidoGlobal).where(PedidoGlobal.factura_local_uuid == factura_local_uuid)
    ).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido maestro no encontrado en el CORE.")

    if pedido.estado in ["FACTURADO", "CANCELADO"]:
        raise HTTPException(
            status_code=400,
            detail=f"Operación inválida. El pedido se encuentra en estado {pedido.estado}."
        )

    detalle = session.exec(
        select(DetallePedido).where(DetallePedido.detalle_local_uuid == detalle_pedido_uuid)
    ).first()

    if not detalle or detalle.pedido_id != pedido.id:
        raise HTTPException(
            status_code=404,
            detail="El ítem (Detalle) especificado no existe o no pertenece a este pedido."
        )

    if not payload.descripcion or not payload.descripcion.strip():
        raise HTTPException(status_code=400, detail="La descripción del modificador no puede estar vacía.")

    modificador = ModificadorItem(
        detalle_pedido_uuid=detalle_pedido_uuid,
        descripcion=payload.descripcion.strip()
    )

    try:
        session.add(modificador)
        session.commit()
        session.refresh(modificador)

        log_auditoria(
            nivel="INFO",
            origen="POST /api/v1/pedidos/modificadores",
            mensaje=f"Instrucción especial añadida al ítem: '{modificador.descripcion}'",
        )
        return modificador

    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error al procesar el modificador en DB: {str(e)}")


@router.get(
    "/{factura_local_uuid}/detalles/{detalle_pedido_uuid}/modificadores",
    response_model=List[ModificadorItemResponse]
)
def listar_modificadores_item(
        factura_local_uuid: str,
        detalle_pedido_uuid: uuid.UUID,
        session: Session = Depends(get_session),
        token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    verificar_rol_empleado(token_obj.credentials, ["ADMIN", "GERENTE", "CAJERO"], session)

    pedido = session.exec(
        select(PedidoGlobal).where(PedidoGlobal.factura_local_uuid == factura_local_uuid)
    ).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado.")

    detalle = session.exec(
        select(DetallePedido).where(DetallePedido.detalle_local_uuid == detalle_pedido_uuid)
    ).first()
    if not detalle or detalle.pedido_id != pedido.id:
        raise HTTPException(status_code=404, detail="Detalle de pedido no encontrado.")

    modificadores = session.exec(
        select(ModificadorItem).where(ModificadorItem.detalle_pedido_uuid == detalle_pedido_uuid)
    ).all()

    return modificadores


@router.post("/{factura_local_uuid}/dividir-cuenta", response_model=SplitBillResponse)
def dividir_cuenta(
    factura_local_uuid: str,
    payload: SplitBillRequest,
    session: Session = Depends(get_session)
):
    if payload.numero_partes < 2:
        raise HTTPException(status_code=400, detail="Se requieren al menos 2 partes para dividir la cuenta.")

    pedido = session.exec(
        select(PedidoGlobal).where(PedidoGlobal.factura_local_uuid == factura_local_uuid)
    ).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado.")

    if pedido.estado in ["FACTURADO", "CANCELADO"]:
        raise HTTPException(status_code=400, detail="No se puede dividir una cuenta ya cerrada.")

    total = pedido.total_general

    if payload.montos_personalizados:
        if len(payload.montos_personalizados) != payload.numero_partes:
            raise HTTPException(
                status_code=400,
                detail=f"Se esperan {payload.numero_partes} montos personalizados, se enviaron {len(payload.montos_personalizados)}."
            )
        suma = sum(Decimal(str(m)) for m in payload.montos_personalizados)
        if abs(suma - total) > Decimal("0.10"):
            raise HTTPException(
                status_code=400,
                detail=f"La suma de los montos personalizados ({suma}) no coincide con el total ({total})."
            )
        monto_por_parte = Decimal(str(payload.montos_personalizados[0]))
        partes = [
            {"parte": i + 1, "monto": float(Decimal(str(payload.montos_personalizados[i])))} 
            for i in range(payload.numero_partes)
        ]
        montos_json = json.dumps(partes)
    else:
        monto_base = (total / payload.numero_partes).quantize(Decimal("0.01"))
        monto_ultimo = total - (monto_base * (payload.numero_partes - 1))
        monto_por_parte = monto_base
        partes = [
            {"parte": i + 1, "monto": float(monto_base) if i < payload.numero_partes - 1 else float(monto_ultimo)}
            for i in range(payload.numero_partes)
        ]
        montos_json = json.dumps(partes)

    division = DivisionCuenta(
        pedido_id=pedido.id,
        numero_partes=payload.numero_partes,
        monto_por_parte=monto_por_parte,
        montos_personalizados_json=montos_json,
        empleado_id=payload.empleado_id
    )
    session.add(division)
    session.commit()
    session.refresh(division)

    log_auditoria(
        nivel="INFO",
        origen=f"POST /api/v1/pedidos/{factura_local_uuid}/dividir-cuenta",
        mensaje=f"Cuenta dividida en {payload.numero_partes} partes. Pedido id={pedido.id}",
        data={"total": float(total), "partes": partes}
    )

    return SplitBillResponse(
        pedido_id=pedido.id,
        factura_local_uuid=str(factura_local_uuid),
        total_general=total,
        numero_partes=payload.numero_partes,
        monto_por_parte=monto_por_parte,
        partes=partes,
        division_id=division.id
    )


@router.get("/{factura_local_uuid}/division-cuenta", response_model=SplitBillResponse)
def obtener_division_cuenta(
    factura_local_uuid: str,
    session: Session = Depends(get_session)
):
    pedido = session.exec(
        select(PedidoGlobal).where(PedidoGlobal.factura_local_uuid == factura_local_uuid)
    ).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado.")

    division = session.exec(
        select(DivisionCuenta)
        .where(DivisionCuenta.pedido_id == pedido.id)
        .order_by(DivisionCuenta.id.desc())
    ).first()

    if not division:
        raise HTTPException(status_code=404, detail="Este pedido no tiene una división de cuenta registrada.")

    partes = json.loads(division.montos_personalizados_json) if division.montos_personalizados_json else []

    return SplitBillResponse(
        pedido_id=pedido.id,
        factura_local_uuid=str(factura_local_uuid),
        total_general=pedido.total_general,
        numero_partes=division.numero_partes,
        monto_por_parte=division.monto_por_parte,
        partes=partes,
        division_id=division.id
    )
