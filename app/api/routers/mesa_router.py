from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, col
import logging
import secrets

from app.db.database import get_session
from app.models.core_models import PedidoGlobal, Mesa
from app.schemas.mesas_schema import (
    MesaVincularRequest, MesaVincularResponse,
    LlamarMeseroRequest, LlamarMeseroResponse,
    MesaCreate, MesaUpdate, MesaAdminResponse
)
from app.services.audit_service import log_auditoria
from app.core.security import oauth2_scheme, verificar_rol_empleado

logger = logging.getLogger("RouterMesasCore")
router = APIRouter(prefix="/api/v1/mesas", tags=["Gestión de Mesas"])


# ─── Endpoints móviles existentes ─────────────────────────────────────────────

@router.post("/vincular", response_model=MesaVincularResponse)
def vincular_mesa(request: MesaVincularRequest, session: Session = Depends(get_session)):
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
    logger.info(f"ALERTA: Mesa {numero_mesa} solicita {request.motivo_llamada}")
    return LlamarMeseroResponse(
        mensaje=f"Notificación de '{request.motivo_llamada}' enviada a la caja."
    )


# ─── CRUD Administrativo ───────────────────────────────────────────────────────

@router.get("/admin", response_model=List[MesaAdminResponse])
def listar_mesas_admin(
    incluir_inactivas: bool = Query(False),
    db: Session = Depends(get_session),
    token: Optional[str] = Depends(oauth2_scheme)
):
    verificar_rol_empleado(token, ["ADMIN", "GERENTE", "CAJERO"], db)
    stmt = select(Mesa)
    if not incluir_inactivas:
        stmt = stmt.where(col(Mesa.activo) == True)
    stmt = stmt.order_by(Mesa.numero)
    return db.exec(stmt).all()


@router.get("/admin/{mesa_id}", response_model=MesaAdminResponse)
def obtener_mesa_admin(
    mesa_id: int,
    db: Session = Depends(get_session),
    token: Optional[str] = Depends(oauth2_scheme)
):
    verificar_rol_empleado(token, ["ADMIN", "GERENTE", "CAJERO"], db)
    mesa = db.get(Mesa, mesa_id)
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa no encontrada.")
    return mesa


@router.post("/admin", response_model=MesaAdminResponse, status_code=201)
def crear_mesa(
    payload: MesaCreate,
    db: Session = Depends(get_session),
    token: Optional[str] = Depends(oauth2_scheme)
):
    verificar_rol_empleado(token, ["ADMIN", "GERENTE"], db)

    existente = db.exec(select(Mesa).where(Mesa.numero == payload.numero)).first()
    if existente:
        raise HTTPException(status_code=400, detail=f"Ya existe una mesa con el número {payload.numero}.")

    qr_token = secrets.token_urlsafe(16)

    mesa = Mesa(
        numero=payload.numero,
        descripcion=payload.descripcion,
        capacidad=payload.capacidad,
        activo=True,
        qr_token=qr_token
    )
    db.add(mesa)
    db.commit()
    db.refresh(mesa)

    log_auditoria(
        nivel="INFO",
        origen="POST /api/v1/mesas/admin",
        mensaje=f"Mesa creada: número={mesa.numero}, id={mesa.id}",
    )
    return mesa


@router.put("/admin/{mesa_id}", response_model=MesaAdminResponse)
def actualizar_mesa(
    mesa_id: int,
    payload: MesaUpdate,
    db: Session = Depends(get_session),
    token: Optional[str] = Depends(oauth2_scheme)
):
    verificar_rol_empleado(token, ["ADMIN", "GERENTE"], db)

    mesa = db.get(Mesa, mesa_id)
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa no encontrada.")

    datos = payload.model_dump(exclude_unset=True)

    if "numero" in datos:
        dup = db.exec(
            select(Mesa).where(Mesa.numero == datos["numero"], col(Mesa.id) != mesa_id)
        ).first()
        if dup:
            raise HTTPException(status_code=400, detail=f"Ya existe otra mesa con el número {datos['numero']}.")

    for campo, valor in datos.items():
        setattr(mesa, campo, valor)

    db.add(mesa)
    db.commit()
    db.refresh(mesa)

    log_auditoria(
        nivel="INFO",
        origen=f"PUT /api/v1/mesas/admin/{mesa_id}",
        mensaje=f"Mesa actualizada: id={mesa_id}",
        data=datos
    )
    return mesa


@router.delete("/admin/{mesa_id}", response_model=dict)
def desactivar_mesa(
    mesa_id: int,
    db: Session = Depends(get_session),
    token: Optional[str] = Depends(oauth2_scheme)
):
    verificar_rol_empleado(token, ["ADMIN", "GERENTE"], db)

    mesa = db.get(Mesa, mesa_id)
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa no encontrada.")
    if not mesa.activo:
        raise HTTPException(status_code=400, detail="La mesa ya está inactiva.")

    mesa.activo = False
    db.add(mesa)
    db.commit()

    log_auditoria(
        nivel="WARNING",
        origen=f"DELETE /api/v1/mesas/admin/{mesa_id}",
        mensaje=f"Mesa desactivada: número={mesa.numero}, id={mesa_id}",
    )
    return {"mensaje": f"Mesa {mesa.numero} desactivada exitosamente.", "id": mesa_id}