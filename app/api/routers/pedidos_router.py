from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db.database import get_session
from app.models.core_models import PedidoGlobal
from app.schemas.pedidos_schema import PedidoCreate, PedidoResponse
from app.logic.orders_manager import OrdersManager
from app.logic.sales_manager import SalesManager

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
            mesa=pedido_in.mesa
        )

        session.commit()
        session.refresh(nuevo_pedido)
        return nuevo_pedido

    except HTTPException as e:
        raise e
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=f"Error al procesar el pedido: {str(e)}")


@router.post("/{id}/facturar", response_model=PedidoResponse)
def facturar_pedido(id: int, empleado_id: int, session: Session = Depends(get_session)):
    try:
        resultado = SalesManager.facturar_pedido(
            session=session,
            pedido_id=id,
            empleado_caja_id=empleado_id
        )
        session.commit()

        return session.get(PedidoGlobal, id)
    except HTTPException as e:
        raise e
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{id}/cancelar")
def cancelar_pedido(id: int, empleado_id: int, motivo: str, session: Session = Depends(get_session)):
    try:
        resultado = SalesManager.cancelar_pedido(
            session=session,
            pedido_id=id,
            empleado_id=empleado_id,
            motivo=motivo
        )
        session.commit()
        return resultado
    except HTTPException as e:
        raise e
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{id}", response_model=PedidoResponse)
def obtener_resumen(id: int, session: Session = Depends(get_session)):
    pedido = session.get(PedidoGlobal, id)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return pedido