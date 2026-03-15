from sqlalchemy import func, Date
from datetime import date
from typing import List
from fastapi import APIRouter, Depends
from sqlmodel import Session, select, desc

from app.db.database import get_session
from app.models.core_models import Producto, InventarioActual, PedidoGlobal
from app.schemas.reportes_schema import VentasDiaResponse, RankingProductosResponse, AlertaStockResponse
from models.core_models import DetallePedido

router = APIRouter(
    prefix="/api/v1/reportes",
    tags=["Módulo de Reportes/Dashboard"]
)

@router.get("/ventas-hoy", response_model=VentasDiaResponse)
def get_ventas_hoy(session: Session = Depends(get_session)):
    consulta = select(func.sum(PedidoGlobal.subtotal))

    consulta = consulta.add_columns(
        func.sum(PedidoGlobal.total_impuestos),
        func.sum(PedidoGlobal.propina_legal),
        func.sum(PedidoGlobal.total_general),
        func.count(PedidoGlobal.id)
    ).where(
        PedidoGlobal.estado == "FACTURADO",
        func.cast(PedidoGlobal.fecha_creacion, Date) == date.today()
    )

    resultado = session.exec(consulta).first()

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
        Producto.nombre,
        InventarioActual.cantidad_disponible,
        InventarioActual.stock_minimo
    ).join(Producto, InventarioActual.producto_id == Producto.id) \
        .where(InventarioActual.cantidad_disponible <= InventarioActual.stock_minimo)

    resultado = session.exec(consulta).all()

    return [
        AlertaStockResponse(
            nombre=registro[0],
            cantidad_disponible=registro[1],
            stock_minimo=registro[2]
        ) for registro in resultado
    ]