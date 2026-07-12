from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, col, desc
from decimal import Decimal

from app.db.database import get_session
from app.models.core_models import (
    PedidoGlobal, DetallePedido, Producto, Empleado, Cliente, AplicacionPromocion,
)
from app.schemas.facturas_schema import (
    FacturaListItem,
    FacturaDetalleResponse,
    FacturaItemResponse,
    FacturaPromocionResponse,
    FacturaCompletaResponse,
)

router = APIRouter(
    prefix="/api/v1/facturas",
    tags=["Módulo de Facturas"]
)


def _resolve_empleado_nombre(session: Session, empleado_id: Optional[int]) -> Optional[str]:
    if not empleado_id:
        return None
    emp = session.get(Empleado, empleado_id)
    return emp.nombre_completo if emp else None


def _resolve_cliente_nombre(session: Session, cliente_id: Optional[int]) -> Optional[str]:
    if not cliente_id:
        return None
    cli = session.get(Cliente, cliente_id)
    return cli.nombre_completo if cli else None


def _get_items(session: Session, pedido_id: int) -> List[FacturaItemResponse]:
    stmt = (
        select(DetallePedido, Producto)
        .join(Producto, DetallePedido.producto_id == Producto.id)
        .where(DetallePedido.pedido_id == pedido_id)
        .order_by(DetallePedido.id)
    )
    rows = session.exec(stmt).all()
    return [
        FacturaItemResponse(
            detalle_id=det.id,
            producto_id=det.producto_id,
            producto_nombre=prod.nombre,
            sku=prod.sku,
            cantidad=det.cantidad,
            precio_unitario_historico=det.precio_unitario_historico,
            impuesto_historico=det.impuesto_historico,
            monto_impuesto=det.monto_impuesto,
            subtotal_linea=det.subtotal_linea,
            detalle_local_uuid=str(det.detalle_local_uuid) if det.detalle_local_uuid else None,
        )
        for det, prod in rows
    ]


def _get_promociones(session: Session, pedido_id: int) -> List[FacturaPromocionResponse]:
    aplics = session.exec(
        select(AplicacionPromocion)
        .where(AplicacionPromocion.pedido_id == pedido_id)
        .order_by(AplicacionPromocion.fecha_hora)
    ).all()
    return [
        FacturaPromocionResponse(
            aplicacion_id=a.id,
            promocion_id=a.promocion_id,
            nombre_promocion=a.nombre_promocion_snap,
            tipo_aplicacion=a.tipo_aplicacion,
            monto_descuento=a.monto_descuento,
            empleado_id=a.empleado_id,
            empleado_autorizador_id=a.empleado_autorizador_id,
            identificador_capturado=a.identificador_capturado,
            notas=a.notas,
            fecha_hora=a.fecha_hora,
        )
        for a in aplics
    ]


@router.get("/", response_model=List[FacturaListItem])
def listar_facturas(
    estado: Optional[str] = Query(
        None,
        description="Filtrar por estado (FACTURADO, CANCELADO, PENDIENTE, POR_FACTURAR). "
                    "Por defecto retorna todos los estados.",
    ),
    canal: Optional[str] = Query(None, description="Filtrar por canal: CAJA | MOVIL"),
    pagina: int = Query(1, ge=1, description="Número de página (1-indexed)"),
    por_pagina: int = Query(50, ge=1, le=200, description="Registros por página"),
    session: Session = Depends(get_session),
):
    """
    Paginated list of invoices/orders.

    Returns compact rows with `id`, `factura_local_uuid`, `fecha_creacion`,
    `estado`, `total_general`, the processing employee name, `canal_origen`,
    and `mesa`. Use `GET /facturas/{id}` for the full header, and
    `GET /facturas/{id}/completo` for a single call with everything.
    """
    stmt = select(PedidoGlobal).order_by(desc(PedidoGlobal.fecha_creacion))

    if estado:
        stmt = stmt.where(PedidoGlobal.estado == estado.upper())
    if canal:
        stmt = stmt.where(PedidoGlobal.canal_origen == canal.upper())

    offset = (pagina - 1) * por_pagina
    stmt = stmt.offset(offset).limit(por_pagina)

    pedidos = session.exec(stmt).all()

    result = []
    for p in pedidos:
        result.append(FacturaListItem(
            id=p.id,
            factura_local_uuid=str(p.factura_local_uuid) if p.factura_local_uuid else None,
            fecha_creacion=p.fecha_creacion,
            estado=p.estado,
            canal_origen=p.canal_origen,
            mesa=p.mesa,
            subtotal=p.subtotal,
            total_impuestos=p.total_impuestos,
            propina_legal=p.propina_legal,
            propina_extra=p.propina_extra,
            total_general=p.total_general,
            empleado_id=p.empleado_id,
            empleado_nombre=_resolve_empleado_nombre(session, p.empleado_id),
            cliente_id=p.cliente_id,
        ))
    return result


@router.get("/{pedido_id}", response_model=FacturaDetalleResponse)
def obtener_factura(
    pedido_id: int,
    session: Session = Depends(get_session),
):
    """
    Full header detail for a single invoice/order by its integer `Id`.

    Includes who processed it (empleado) and the client (if any), plus the
    complete financial breakdown (subtotal, impuestos, propinas, total).
    """
    pedido = session.get(PedidoGlobal, pedido_id)
    if not pedido:
        raise HTTPException(status_code=404, detail=f"Factura con id={pedido_id} no encontrada.")

    return FacturaDetalleResponse(
        id=pedido.id,
        factura_local_uuid=str(pedido.factura_local_uuid) if pedido.factura_local_uuid else None,
        fecha_creacion=pedido.fecha_creacion,
        estado=pedido.estado,
        canal_origen=pedido.canal_origen,
        mesa=pedido.mesa,
        subtotal=pedido.subtotal,
        total_impuestos=pedido.total_impuestos,
        propina_legal=pedido.propina_legal,
        propina_extra=pedido.propina_extra,
        total_general=pedido.total_general,
        empleado_id=pedido.empleado_id,
        empleado_nombre=_resolve_empleado_nombre(session, pedido.empleado_id),
        cliente_id=pedido.cliente_id,
        cliente_nombre=_resolve_cliente_nombre(session, pedido.cliente_id),
    )


@router.get("/{pedido_id}/items", response_model=List[FacturaItemResponse])
def obtener_items_factura(
    pedido_id: int,
    session: Session = Depends(get_session),
):
    """
    All line items (DetallePedido) for a given invoice.

    Each item includes the product name, SKU, quantity, historical unit price,
    tax rate at time of sale, absolute tax amount, and the line subtotal.
    """
    pedido = session.get(PedidoGlobal, pedido_id)
    if not pedido:
        raise HTTPException(status_code=404, detail=f"Factura con id={pedido_id} no encontrada.")

    return _get_items(session, pedido_id)


@router.get("/{pedido_id}/promociones", response_model=List[FacturaPromocionResponse])
def obtener_promociones_factura(
    pedido_id: int,
    session: Session = Depends(get_session),
):
    """
    All promotions that were applied to a given invoice, taken from the
    immutable `Aplicaciones_Promocion` audit ledger.

    Returns each promotion's name (snapshotted at time of application), the
    discount amount, which employee applied it, who authorized it (if any),
    and any captured identifier (e.g. student ID for eligibility promos).
    """
    pedido = session.get(PedidoGlobal, pedido_id)
    if not pedido:
        raise HTTPException(status_code=404, detail=f"Factura con id={pedido_id} no encontrada.")

    return _get_promociones(session, pedido_id)


@router.get("/{pedido_id}/completo", response_model=FacturaCompletaResponse)
def obtener_factura_completa(
    pedido_id: int,
    session: Session = Depends(get_session),
):
    """
    All-in-one invoice view: header + line items + applied promotions in a
    single call. Designed for receipt printing, invoice display, and any view
    that needs the full picture without making multiple requests.
    """
    pedido = session.get(PedidoGlobal, pedido_id)
    if not pedido:
        raise HTTPException(status_code=404, detail=f"Factura con id={pedido_id} no encontrada.")

    items = _get_items(session, pedido_id)
    promociones = _get_promociones(session, pedido_id)
    total_descuentos = sum(p.monto_descuento for p in promociones) or Decimal("0")

    return FacturaCompletaResponse(
        id=pedido.id,
        factura_local_uuid=str(pedido.factura_local_uuid) if pedido.factura_local_uuid else None,
        fecha_creacion=pedido.fecha_creacion,
        estado=pedido.estado,
        canal_origen=pedido.canal_origen,
        mesa=pedido.mesa,
        subtotal=pedido.subtotal,
        total_impuestos=pedido.total_impuestos,
        propina_legal=pedido.propina_legal,
        propina_extra=pedido.propina_extra,
        total_general=pedido.total_general,
        empleado_id=pedido.empleado_id,
        empleado_nombre=_resolve_empleado_nombre(session, pedido.empleado_id),
        cliente_id=pedido.cliente_id,
        cliente_nombre=_resolve_cliente_nombre(session, pedido.cliente_id),
        items=items,
        promociones=promociones,
        total_descuentos=total_descuentos,
    )
