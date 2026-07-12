from sqlalchemy import func, Date, extract
from datetime import date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select, desc, col

from app.db.database import get_session
from app.models.core_models import (
    Producto, InventarioActual, PedidoGlobal, DetallePedido,
    Ingrediente, Categoria, Promocion, AplicacionPromocion, MovimientoIngrediente,
)
from app.schemas.reportes_schema import (
    VentasDiaResponse,
    RankingProductosResponse,
    AlertaStockResponse,
    AlertaIngredienteResponse,
    VentasPeriodoResponse,
    VentasDiaSerie,
    VentasHoraSerie,
    RankingProductosPeriodoResponse,
    VentasCanalResponse,
    VentasCategoriaResponse,
    KpisGeneralesResponse,
    PedidoAbiertoResumen,
    MovimientoRecienteResponse,
    PromocionActivaResumen,
)
from decimal import Decimal
from datetime import datetime

router = APIRouter(
    prefix="/api/v1/reportes",
    tags=["Módulo de Reportes/Dashboard"]
)



@router.get("/ventas-hoy", response_model=VentasDiaResponse)
def get_ventas_hoy(session: Session = Depends(get_session)):
    consulta = select(
        func.sum(PedidoGlobal.subtotal),
        func.sum(PedidoGlobal.total_impuestos),
        func.sum(PedidoGlobal.propina_legal),
        func.sum(PedidoGlobal.total_general),
        func.count(PedidoGlobal.id)
    ).where(
        PedidoGlobal.estado == "FACTURADO",
        func.cast(PedidoGlobal.fecha_creacion, Date) == date.today()
    )

    resultado = session.exec(consulta).first()

    if not resultado or resultado[0] is None:
        return VentasDiaResponse(
            subtotal=0,
            total_impuestos=0,
            propina_legal=0,
            total_general=0,
            conteo_pedidos=0
        )

    subtotal, impuestos, propina, total, conteo = resultado

    return VentasDiaResponse(
        subtotal=subtotal or 0,
        total_impuestos=impuestos or 0,
        propina_legal=propina or 0,
        total_general=total or 0,
        conteo_pedidos=conteo or 0
    )


@router.get("/top-productos-vendidos", response_model=List[RankingProductosResponse])
def get_top_productos_vendidos(session: Session = Depends(get_session)):
    consulta = select(
        Producto.nombre,
        func.sum(DetallePedido.cantidad).label("cantidad_vendida")
    ).join(Producto, DetallePedido.producto_id == Producto.id) \
        .group_by(Producto.nombre) \
        .order_by(desc("cantidad_vendida")) \
        .limit(10)

    resultado = session.exec(consulta).all()

    return [RankingProductosResponse(nombre=registro[0], cantidad_vendida=registro[1]) for registro in resultado]


@router.get("/productos-stock-bajo", response_model=List[AlertaStockResponse])
def get_productos_stock_bajo(session: Session = Depends(get_session)):
    consulta = select(
        Producto.id,
        Producto.sku,
        Producto.nombre,
        InventarioActual.cantidad_disponible,
        InventarioActual.stock_minimo
    ).join(Producto, InventarioActual.producto_id == Producto.id) \
        .where(InventarioActual.cantidad_disponible <= InventarioActual.stock_minimo)

    resultado = session.exec(consulta).all()

    return [
        AlertaStockResponse(
            producto_id=row[0],
            sku=row[1],
            nombre=row[2],
            cantidad_disponible=row[3],
            stock_minimo=row[4]
        ) for row in resultado
    ]


@router.get("/ingredientes-stock-bajo", response_model=List[AlertaIngredienteResponse])
def get_ingredientes_stock_bajo(session: Session = Depends(get_session)):
    """
    Ingredient-based stock alerts: active ingredients at or below their minimum
    quantity. This is the primary alert endpoint for the new inventory system.
    """
    ingredientes = session.exec(
        select(Ingrediente).where(
            col(Ingrediente.activo) == True,
            col(Ingrediente.cantidad_actual) <= col(Ingrediente.cantidad_minima),
        )
    ).all()

    return [
        AlertaIngredienteResponse(
            id=ing.id,
            nombre=ing.nombre,
            unidad_medida=ing.unidad_medida,
            cantidad_actual=ing.cantidad_actual,
            cantidad_minima=ing.cantidad_minima,
            cantidad_reorden=ing.cantidad_reorden,
            deficit=max(Decimal("0"), ing.cantidad_reorden - ing.cantidad_actual),
        )
        for ing in ingredientes
    ]


# ─────────────────────────────────────────────────────────────────
# NEW DASHBOARD / GRAPH ENDPOINTS
# ─────────────────────────────────────────────────────────────────

@router.get("/ventas-periodo", response_model=VentasPeriodoResponse)
def get_ventas_periodo(
    fecha_inicio: date = Query(..., description="Fecha de inicio (YYYY-MM-DD)"),
    fecha_fin: date = Query(..., description="Fecha de fin (YYYY-MM-DD)"),
    session: Session = Depends(get_session)
):
    """
    Aggregate totals (subtotal, impuestos, propinas, total, conteo) for any
    date range. Used by filterable summary cards on the dashboard.
    """
    if fecha_fin < fecha_inicio:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="fecha_fin no puede ser anterior a fecha_inicio.")

    consulta = select(
        func.sum(PedidoGlobal.subtotal),
        func.sum(PedidoGlobal.total_impuestos),
        func.sum(PedidoGlobal.propina_legal),
        func.sum(PedidoGlobal.total_general),
        func.count(PedidoGlobal.id)
    ).where(
        PedidoGlobal.estado == "FACTURADO",
        func.cast(PedidoGlobal.fecha_creacion, Date) >= fecha_inicio,
        func.cast(PedidoGlobal.fecha_creacion, Date) <= fecha_fin,
    )

    row = session.exec(consulta).first()
    subtotal, impuestos, propina, total, conteo = row if row else (0, 0, 0, 0, 0)

    return VentasPeriodoResponse(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        subtotal=subtotal or Decimal("0"),
        total_impuestos=impuestos or Decimal("0"),
        propina_legal=propina or Decimal("0"),
        total_general=total or Decimal("0"),
        conteo_pedidos=conteo or 0,
    )


@router.get("/ventas-por-dia", response_model=List[VentasDiaSerie])
def get_ventas_por_dia(
    dias: int = Query(30, ge=1, le=365, description="Número de días hacia atrás (máx 365)"),
    session: Session = Depends(get_session)
):
    """
    Daily revenue time-series for the last N days. Ideal for a line/bar chart
    on the dashboard. Only includes FACTURADO orders.
    """
    fecha_inicio = date.today() - timedelta(days=dias - 1)

    consulta = select(
        func.cast(PedidoGlobal.fecha_creacion, Date).label("dia"),
        func.sum(PedidoGlobal.subtotal).label("subtotal"),
        func.sum(PedidoGlobal.total_general).label("total_general"),
        func.count(PedidoGlobal.id).label("conteo"),
    ).where(
        PedidoGlobal.estado == "FACTURADO",
        func.cast(PedidoGlobal.fecha_creacion, Date) >= fecha_inicio,
    ).group_by(
        func.cast(PedidoGlobal.fecha_creacion, Date)
    ).order_by(
        func.cast(PedidoGlobal.fecha_creacion, Date)
    )

    rows = session.exec(consulta).all()

    # Build a full series — fill zeros for days without data
    series_map = {row[0]: row for row in rows}
    result = []
    for i in range(dias):
        dia = fecha_inicio + timedelta(days=i)
        if dia in series_map:
            r = series_map[dia]
            result.append(VentasDiaSerie(
                fecha=r[0],
                subtotal=r[1] or Decimal("0"),
                total_general=r[2] or Decimal("0"),
                conteo_pedidos=r[3] or 0,
            ))
        else:
            result.append(VentasDiaSerie(
                fecha=dia,
                subtotal=Decimal("0"),
                total_general=Decimal("0"),
                conteo_pedidos=0,
            ))
    return result


@router.get("/ventas-por-hora", response_model=List[VentasHoraSerie])
def get_ventas_por_hora(
    dia: Optional[date] = Query(None, description="Día a analizar (YYYY-MM-DD). Por defecto: hoy."),
    session: Session = Depends(get_session)
):
    """
    Hourly order distribution for a given day (default: today). Perfect for a
    bar chart showing peak hours at the bar.
    """
    target_day = dia or date.today()

    consulta = select(
        extract("hour", PedidoGlobal.fecha_creacion).label("hora"),
        func.count(PedidoGlobal.id).label("conteo"),
        func.sum(PedidoGlobal.total_general).label("total_general"),
    ).where(
        PedidoGlobal.estado == "FACTURADO",
        func.cast(PedidoGlobal.fecha_creacion, Date) == target_day,
    ).group_by(
        extract("hour", PedidoGlobal.fecha_creacion)
    ).order_by(
        extract("hour", PedidoGlobal.fecha_creacion)
    )

    rows = session.exec(consulta).all()
    hour_map = {int(r[0]): r for r in rows}

    # Return all 24 hours (zeros where no data)
    return [
        VentasHoraSerie(
            hora=h,
            conteo_pedidos=hour_map[h][1] if h in hour_map else 0,
            total_general=hour_map[h][2] if h in hour_map else Decimal("0"),
        )
        for h in range(24)
    ]


@router.get("/top-productos-periodo", response_model=List[RankingProductosPeriodoResponse])
def get_top_productos_periodo(
    fecha_inicio: date = Query(..., description="Fecha de inicio (YYYY-MM-DD)"),
    fecha_fin: date = Query(..., description="Fecha de fin (YYYY-MM-DD)"),
    limite: int = Query(10, ge=1, le=50, description="Cantidad máxima de productos"),
    session: Session = Depends(get_session)
):
    """
    Top-selling products within a date range, ordered by units sold.
    Includes categoria, ingreso total, and producto_id for deep-linking.
    """
    consulta = select(
        Producto.id,
        Producto.nombre,
        Categoria.nombre,
        func.sum(DetallePedido.cantidad).label("cantidad_vendida"),
        func.sum(DetallePedido.subtotal_linea).label("ingreso_total"),
    ).join(Producto, DetallePedido.producto_id == Producto.id) \
     .join(Categoria, Producto.categoria_id == Categoria.id) \
     .join(PedidoGlobal, DetallePedido.pedido_id == PedidoGlobal.id) \
     .where(
        PedidoGlobal.estado == "FACTURADO",
        func.cast(PedidoGlobal.fecha_creacion, Date) >= fecha_inicio,
        func.cast(PedidoGlobal.fecha_creacion, Date) <= fecha_fin,
    ).group_by(
        Producto.id, Producto.nombre, Categoria.nombre
    ).order_by(
        desc("cantidad_vendida")
    ).limit(limite)

    rows = session.exec(consulta).all()

    return [
        RankingProductosPeriodoResponse(
            producto_id=r[0],
            nombre=r[1],
            categoria=r[2],
            cantidad_vendida=r[3] or 0,
            ingreso_total=r[4] or Decimal("0"),
        )
        for r in rows
    ]


@router.get("/ventas-por-canal", response_model=List[VentasCanalResponse])
def get_ventas_por_canal(
    fecha_inicio: Optional[date] = Query(None, description="Filtrar desde esta fecha (YYYY-MM-DD)"),
    fecha_fin: Optional[date] = Query(None, description="Filtrar hasta esta fecha (YYYY-MM-DD)"),
    session: Session = Depends(get_session)
):
    """
    Revenue breakdown by sales channel (CAJA, MOVIL). Useful for a pie/donut chart.
    If no dates are provided, returns all-time totals.
    """
    consulta = select(
        PedidoGlobal.canal_origen,
        func.count(PedidoGlobal.id).label("conteo"),
        func.sum(PedidoGlobal.total_general).label("total_general"),
    ).where(
        PedidoGlobal.estado == "FACTURADO",
        PedidoGlobal.canal_origen.in_(["CAJA", "MOVIL"]),
    )

    if fecha_inicio:
        consulta = consulta.where(func.cast(PedidoGlobal.fecha_creacion, Date) >= fecha_inicio)
    if fecha_fin:
        consulta = consulta.where(func.cast(PedidoGlobal.fecha_creacion, Date) <= fecha_fin)

    consulta = consulta.group_by(PedidoGlobal.canal_origen).order_by(PedidoGlobal.canal_origen)

    rows = session.exec(consulta).all()

    # Always return both channels — zero if no data
    data_map = {r[0]: r for r in rows}
    result = []
    for canal in ["CAJA", "MOVIL"]:
        if canal in data_map:
            r = data_map[canal]
            result.append(VentasCanalResponse(
                canal=r[0],
                conteo_pedidos=r[1] or 0,
                total_general=r[2] or Decimal("0"),
            ))
        else:
            result.append(VentasCanalResponse(
                canal=canal,
                conteo_pedidos=0,
                total_general=Decimal("0"),
            ))
    return result


@router.get("/ventas-por-categoria", response_model=List[VentasCategoriaResponse])
def get_ventas_por_categoria(
    fecha_inicio: Optional[date] = Query(None, description="Filtrar desde esta fecha"),
    fecha_fin: Optional[date] = Query(None, description="Filtrar hasta esta fecha"),
    session: Session = Depends(get_session)
):
    """
    Revenue grouped by product category. Ideal for a bar chart showing which
    categories drive the most income at the bar.
    """
    consulta = select(
        Categoria.id,
        Categoria.nombre,
        func.sum(DetallePedido.cantidad).label("conteo_productos"),
        func.sum(DetallePedido.subtotal_linea).label("ingreso_total"),
    ).join(Producto, DetallePedido.producto_id == Producto.id) \
     .join(Categoria, Producto.categoria_id == Categoria.id) \
     .join(PedidoGlobal, DetallePedido.pedido_id == PedidoGlobal.id) \
     .where(PedidoGlobal.estado == "FACTURADO")

    if fecha_inicio:
        consulta = consulta.where(func.cast(PedidoGlobal.fecha_creacion, Date) >= fecha_inicio)
    if fecha_fin:
        consulta = consulta.where(func.cast(PedidoGlobal.fecha_creacion, Date) <= fecha_fin)

    consulta = consulta.group_by(
        Categoria.id, Categoria.nombre
    ).order_by(desc("ingreso_total"))

    rows = session.exec(consulta).all()

    return [
        VentasCategoriaResponse(
            categoria_id=r[0],
            categoria=r[1],
            conteo_productos_vendidos=r[2] or 0,
            ingreso_total=r[3] or Decimal("0"),
        )
        for r in rows
    ]


@router.get("/kpis-generales", response_model=KpisGeneralesResponse)
def get_kpis_generales(session: Session = Depends(get_session)):
    """
    Single dashboard scoreboard: today's revenue, open orders, stock alerts,
    and active promotions — all in one fast call.
    """
    hoy = date.today()

    # --- ventas hoy ---
    row_ventas = session.exec(
        select(
            func.sum(PedidoGlobal.total_general),
            func.count(PedidoGlobal.id),
        ).where(
            PedidoGlobal.estado == "FACTURADO",
            func.cast(PedidoGlobal.fecha_creacion, Date) == hoy,
        )
    ).first()
    ventas_total = row_ventas[0] or Decimal("0") if row_ventas else Decimal("0")
    ventas_conteo = row_ventas[1] or 0 if row_ventas else 0

    # --- pedidos abiertos ---
    pedidos_abiertos = session.exec(
        select(func.count(PedidoGlobal.id)).where(PedidoGlobal.estado == "PENDIENTE")
    ).first() or 0

    pedidos_por_facturar = session.exec(
        select(func.count(PedidoGlobal.id)).where(PedidoGlobal.estado == "POR_FACTURAR")
    ).first() or 0

    # --- stock alerts ---
    productos_bajo = session.exec(
        select(func.count(InventarioActual.id)).where(
            InventarioActual.cantidad_disponible <= InventarioActual.stock_minimo
        )
    ).first() or 0

    ingredientes_bajo = session.exec(
        select(func.count(Ingrediente.id)).where(
            col(Ingrediente.activo) == True,
            col(Ingrediente.cantidad_actual) <= col(Ingrediente.cantidad_minima),
        )
    ).first() or 0

    # --- active promos ---
    ahora = datetime.utcnow()
    promos_activas = session.exec(
        select(func.count(Promocion.id)).where(
            col(Promocion.activo) == True,
            Promocion.fecha_inicio <= ahora,
        )
    ).first() or 0

    return KpisGeneralesResponse(
        ventas_hoy_total=ventas_total,
        ventas_hoy_conteo=ventas_conteo,
        pedidos_abiertos=int(pedidos_abiertos),
        pedidos_por_facturar=int(pedidos_por_facturar),
        productos_stock_bajo=int(productos_bajo),
        ingredientes_stock_bajo=int(ingredientes_bajo),
        promociones_activas=int(promos_activas),
    )


@router.get("/pedidos-abiertos", response_model=List[PedidoAbiertoResumen])
def get_pedidos_abiertos(
    incluir_por_facturar: bool = Query(True, description="Incluir pedidos en estado POR_FACTURAR"),
    session: Session = Depends(get_session)
):
    """
    List of currently open orders (PENDIENTE + optionally POR_FACTURAR).
    Useful as a live-orders widget on the dashboard.
    """
    estados = ["PENDIENTE"]
    if incluir_por_facturar:
        estados.append("POR_FACTURAR")

    pedidos = session.exec(
        select(PedidoGlobal)
        .where(PedidoGlobal.estado.in_(estados))
        .order_by(PedidoGlobal.fecha_creacion)
    ).all()

    return [
        PedidoAbiertoResumen(
            id=p.id,
            factura_local_uuid=str(p.factura_local_uuid) if p.factura_local_uuid else None,
            canal_origen=p.canal_origen,
            mesa=p.mesa,
            estado=p.estado,
            total_general=p.total_general,
            fecha_creacion=p.fecha_creacion,
            empleado_id=p.empleado_id,
        )
        for p in pedidos
    ]


@router.get("/movimientos-recientes", response_model=List[MovimientoRecienteResponse])
def get_movimientos_recientes(
    limite: int = Query(20, ge=1, le=100, description="Cantidad de movimientos a retornar"),
    session: Session = Depends(get_session)
):
    """
    Most recent ingredient movements for an activity-feed widget on the dashboard.
    Shows who moved what and when.
    """
    consulta = select(
        MovimientoIngrediente,
        Ingrediente.nombre,
        Ingrediente.unidad_medida,
    ).join(Ingrediente, MovimientoIngrediente.ingrediente_id == Ingrediente.id) \
     .order_by(desc(MovimientoIngrediente.fecha_movimiento)) \
     .limit(limite)

    rows = session.exec(consulta).all()

    return [
        MovimientoRecienteResponse(
            id=mov.id,
            ingrediente_id=mov.ingrediente_id,
            ingrediente_nombre=nombre,
            tipo_movimiento=mov.tipo_movimiento,
            cantidad=mov.cantidad,
            unidad_medida=unidad,
            fecha_movimiento=mov.fecha_movimiento,
            empleado_id=mov.empleado_id,
            notas=mov.notas,
        )
        for mov, nombre, unidad in rows
    ]


@router.get("/promociones-activas", response_model=List[PromocionActivaResumen])
def get_promociones_activas(session: Session = Depends(get_session)):
    """
    All currently active promotions with their usage count and total discount
    applied today. Useful for a quick promo-health panel on the dashboard.
    """
    ahora = datetime.utcnow()
    hoy = date.today()

    promos = session.exec(
        select(Promocion).where(
            col(Promocion.activo) == True,
            Promocion.fecha_inicio <= ahora,
        ).order_by(desc(Promocion.prioridad))
    ).all()

    result = []
    for promo in promos:
        # Count usages and total discount for today
        row = session.exec(
            select(
                func.count(AplicacionPromocion.id),
                func.sum(AplicacionPromocion.monto_descuento),
            ).where(
                AplicacionPromocion.promocion_id == promo.id,
                func.cast(AplicacionPromocion.fecha_hora, Date) == hoy,
            )
        ).first()

        usos_hoy = row[0] or 0 if row else 0
        descuento_hoy = row[1] or Decimal("0") if row else Decimal("0")

        result.append(PromocionActivaResumen(
            id=promo.id,
            nombre=promo.nombre,
            tipo_descuento=promo.tipo_descuento,
            valor=promo.valor,
            aplica_a=promo.aplica_a,
            tipo_aplicacion=promo.tipo_aplicacion,
            usos_hoy=usos_hoy,
            descuento_total_hoy=descuento_hoy,
        ))

    return result