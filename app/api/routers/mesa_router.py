from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
import logging

from app.db.database import get_session
from app.models.core_models import PedidoGlobal
from app.schemas.mesas_schema import (
    MesaVincularRequest, MesaVincularResponse,
    LlamarMeseroRequest, LlamarMeseroResponse
)

logger = logging.getLogger("RouterMesasCore")
router = APIRouter(prefix="/api/v1/mesas", tags=["Gestión de Mesas"])

@router.post("/vincular", response_model=MesaVincularResponse)
def vincular_mesa(request: MesaVincularRequest, session: Session = Depends(get_session)):
    """
    Verifica si la mesa está libre u ocupada en el sistema central.
    """
    # Buscamos si hay un pedido activo (que no esté facturado ni cancelado)
    # Ajusta los estados ("PENDIENTE", "ABIERTA") según los que uses en tu modelo Pedido.
    statement = select(PedidoGlobal).where(
        PedidoGlobal.mesa == request.numero_mesa,
        PedidoGlobal.estado.in_(["PENDIENTE", "ABIERTA", "EN_PREPARACION"])
    )
    pedido_activo = session.exec(statement).first()

    if pedido_activo:
        return MesaVincularResponse(
            mensaje="Mesa ocupada. Uniéndose a la cuenta activa.",
            estado_mesa="ABIERTA",
            numero_mesa=request.numero_mesa,
            factura_local_uuid_activa=pedido_activo.factura_local_uuid
        )
    else:
        return MesaVincularResponse(
            mensaje="Mesa libre. Listo para pedir.",
            estado_mesa="LIBRE",
            numero_mesa=request.numero_mesa,
            factura_local_uuid_activa=None
        )

@router.post("/{numero_mesa}/llamar-mesero", response_model=LlamarMeseroResponse)
def llamar_mesero(numero_mesa: int, request: LlamarMeseroRequest):
    """
    Registra la alerta en la nube (en un caso real, dispararía un Webhook o Websocket).
    """
    logger.info(f"ALERTA: Mesa {numero_mesa} solicita {request.motivo_llamada}")
    return LlamarMeseroResponse(
        mensaje=f"Notificación de '{request.motivo_llamada}' enviada a la caja."
    )