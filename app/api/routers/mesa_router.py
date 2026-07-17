import os
import secrets
import qrcode
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials
from sqlmodel import Session, select, col

from app.db.database import get_session
from app.models.core_models import PedidoGlobal, Mesa
from app.schemas.mesas_schema import (
    MesaVincularRequest, MesaVincularResponse,
    LlamarMeseroRequest, LlamarMeseroResponse,
    MesaCreate, MesaUpdate, MesaAdminResponse
)
from app.core.security import security_bearer, verificar_rol_empleado
from app.services.audit_service import log_auditoria

logger = logging.getLogger("RouterMesasCore")
router = APIRouter(prefix="/api/v1/mesas", tags=["Gestión de Mesas"])

# ─── Configuración de Códigos QR ──────────────────────────────────────────────
URL_BASE = "https://nocturnal-bar.app/scan"
SUCURSAL_ID = 1
# Ruta absoluta (independiente del cwd desde el que se lance uvicorn):
# app/api/routers/mesa_router.py -> sube 3 niveles hasta la raiz del proyecto (QA CORE)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
CARPETA_QRS = os.path.join(_PROJECT_ROOT, "qrs_mesas")


def generar_imagen_qr(numero_mesa: int, qr_token: str) -> str:
    """Genera el archivo físico PNG del código QR y devuelve su ruta."""
    if not os.path.exists(CARPETA_QRS):
        os.makedirs(CARPETA_QRS)

    # El payload incluye ruteo para el frontend y el token seguro para el backend
    payload_url = f"{URL_BASE}?sucursal={SUCURSAL_ID}&mesa={numero_mesa}&token={qr_token}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(payload_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    nombre_archivo = f"{CARPETA_QRS}/QR_Sucursal_{SUCURSAL_ID}_Mesa_{numero_mesa}.png"
    img.save(nombre_archivo)

    return nombre_archivo


# ─── Endpoints Móviles (Flujo QR Protegido) ───────────────────────────────────

@router.post("/vincular", response_model=MesaVincularResponse)
def vincular_mesa(request: MesaVincularRequest, session: Session = Depends(get_session)):
    """ Permite a un cliente o dispositivo unirse a una mesa escaneando su QR. """
    # Se busca la mesa estrictamente por el token criptográfico del QR
    mesa = session.exec(select(Mesa).where(Mesa.qr_token == request.codigo_qr_mesa, Mesa.activo == True)).first()

    if not mesa:
        raise HTTPException(status_code=404, detail="Código QR inválido o mesa inactiva.")

    statement = select(PedidoGlobal).where(
        PedidoGlobal.mesa == mesa.numero,
        PedidoGlobal.estado.in_(["PENDIENTE", "ABIERTA", "EN_PREPARACION"])
    )
    pedido_activo = session.exec(statement).first()

    if pedido_activo:
        return MesaVincularResponse(
            mensaje="Mesa ocupada. Uniéndose a la cuenta activa.",
            estado_mesa="ABIERTA",
            numero_mesa=mesa.numero,
            factura_local_uuid_activa=pedido_activo.factura_local_uuid
        )
    else:
        return MesaVincularResponse(
            mensaje="Mesa libre. Listo para pedir.",
            estado_mesa="LIBRE",
            numero_mesa=mesa.numero,
            factura_local_uuid_activa=None
        )


@router.post("/llamar-mesero", response_model=LlamarMeseroResponse)
def llamar_mesero(request: LlamarMeseroRequest, session: Session = Depends(get_session)):
    """ Permite a un cliente solicitar asistencia asegurando presencia física en la mesa. """
    mesa = session.exec(
        select(Mesa).where(Mesa.qr_token == request.qr_token, Mesa.activo == True)
    ).first()

    if not mesa:
        raise HTTPException(status_code=404, detail="Código QR inválido o mesa inactiva.")

    logger.info(f"ALERTA OPERATIVA: Mesa {mesa.numero} solicita '{request.motivo_llamada}'")

    return LlamarMeseroResponse(
        mensaje=f"Notificación de '{request.motivo_llamada}' enviada a la caja para la Mesa {mesa.numero}."
    )


# ─── CRUD Administrativo (CORE Mainframe) ─────────────────────────────────────

@router.get("/admin", response_model=List[MesaAdminResponse])
def listar_mesas_admin(
        incluir_inactivas: bool = Query(False),
        db: Session = Depends(get_session),
        token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    if not token_obj or not token_obj.credentials:
        raise HTTPException(status_code=401, detail="Token Bearer ausente o inválido")

    verificar_rol_empleado(token_obj.credentials, ["ADMIN", "GERENTE", "CAJERO"], db)

    stmt = select(Mesa)
    if not incluir_inactivas:
        stmt = stmt.where(col(Mesa.activo) == True)
    stmt = stmt.order_by(Mesa.numero)
    return db.exec(stmt).all()


@router.get("/admin/{mesa_id}", response_model=MesaAdminResponse)
def obtener_mesa_admin(
        mesa_id: int,
        db: Session = Depends(get_session),
        token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    verificar_rol_empleado(token_obj.credentials, ["ADMIN", "GERENTE", "CAJERO"], db)

    mesa = db.get(Mesa, mesa_id)
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa no encontrada.")
    return mesa


@router.post("/admin", response_model=MesaAdminResponse, status_code=201)
def crear_mesa(
        payload: MesaCreate,
        db: Session = Depends(get_session),
        token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):

    empleado_info = verificar_rol_empleado(token_obj.credentials, ["ADMIN", "GERENTE"], db)

    existente = db.exec(select(Mesa).where(Mesa.numero == payload.numero)).first()
    if existente:
        raise HTTPException(status_code=400, detail=f"Ya existe una mesa con el número {payload.numero}.")

    # Generación del token criptográfico y guardado en DB
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

    # Generamos la imagen física PNG de forma automática al crear la mesa.
    # Esto es un artefacto auxiliar (el qr_token ya quedó guardado en la mesa),
    # así que si falla (permisos, carpeta no escribible, etc.) no debe hacer
    # fallar la creación de la mesa, que ya fue confirmada en la base de datos.
    try:
        ruta_imagen = generar_imagen_qr(numero_mesa=mesa.numero, qr_token=mesa.qr_token)
        log_auditoria(
            nivel="INFO",
            origen="POST /api/v1/mesas/admin",
            mensaje=f"Mesa creada y QR generado ({ruta_imagen}): número={mesa.numero}, id={mesa.id}",
        )
    except Exception as exc:
        logger.exception(f"No se pudo generar la imagen QR para la mesa {mesa.numero} (id={mesa.id})")
        log_auditoria(
            nivel="ERROR",
            origen="POST /api/v1/mesas/admin",
            mensaje=f"Mesa creada (id={mesa.id}) pero falló la generación del QR físico: {exc}",
        )

    return mesa


@router.put("/admin/{mesa_id}", response_model=MesaAdminResponse)
def actualizar_mesa(
        mesa_id: int,
        payload: MesaUpdate,
        db: Session = Depends(get_session),
        token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):

    empleado_info = verificar_rol_empleado(token_obj.credentials, ["ADMIN", "GERENTE"], db)

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
        origen="PUT /api/v1/mesas/admin",
        mensaje=f"Mesa modificada: id={mesa_id}, número={mesa.numero}",
        data=datos
    )
    return mesa


@router.delete("/admin/{mesa_id}", response_model=dict)
def desactivar_mesa(
        mesa_id: int,
        db: Session = Depends(get_session),
        token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    empleado_info = verificar_rol_empleado(token_obj.credentials, ["ADMIN", "GERENTE"], db)

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
        origen="DELETE /api/v1/mesas/admin",
        mensaje=f"Mesa desactivada: número={mesa.numero}, id={mesa_id}"
    )
    return {"mensaje": f"Mesa {mesa.numero} desactivada exitosamente.", "id": mesa_id}