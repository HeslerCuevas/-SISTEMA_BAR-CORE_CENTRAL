from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials
from sqlmodel import Session, select, col
from decimal import Decimal

from app.services.promociones_service import _es_happy_hour, _promocion_vigente
from datetime import datetime, timezone

from app.db.database import get_session
from app.core.timezone import get_local_now
from app.models.core_models import Promocion, PromocionProducto, PromocionCategoria, Producto, Categoria
from app.schemas.promociones_schema import (
    PromocionCreate, PromocionUpdate, PromocionResponse, PromocionAplicadaResponse,
    SupervisorSessionSync
)
from app.services.audit_service import log_auditoria
from app.services.promociones_service import (
    evaluar_promociones_para_item, obtener_mejor_promocion, evaluar_promociones_globales
)
from app.core.security import verificar_rol_empleado, security_bearer

router = APIRouter(prefix="/api/v1/promociones", tags=["Promociones y Descuentos"])


@router.get("/", response_model=List[PromocionResponse])
def listar_promociones(
    solo_activas: bool = Query(True),
    db: Session = Depends(get_session)
):
    stmt = select(Promocion)
    if solo_activas:
        stmt = stmt.where(col(Promocion.activo) == True)
    stmt = stmt.order_by(Promocion.prioridad.desc())
    promociones = db.exec(stmt).all()
    
    result = []
    for p in promociones:
        p_dict = p.model_dump()
        p_dict["producto_ids"] = [
            pp.producto_id for pp in db.exec(select(PromocionProducto).where(PromocionProducto.promocion_id == p.id)).all()
        ]
        p_dict["categoria_ids"] = [
            pc.categoria_id for pc in db.exec(select(PromocionCategoria).where(PromocionCategoria.promocion_id == p.id)).all()
        ]
        result.append(p_dict)
    return result


@router.get("/codigos", response_model=list)
def listar_codigos_promocionales(db: Session = Depends(get_session)):
    from app.models.core_models import CodigoPromocional
    stmt = select(CodigoPromocional)
    codigos = db.exec(stmt).all()
    return codigos


@router.get("/elegibilidad", response_model=list)
def listar_elegibilidad(db: Session = Depends(get_session)):
    from app.models.core_models import PromocionElegibilidad
    stmt = select(PromocionElegibilidad)
    return db.exec(stmt).all()


@router.get("/{promocion_id}", response_model=PromocionResponse)
def obtener_promocion(promocion_id: int, db: Session = Depends(get_session)):
    promo = db.get(Promocion, promocion_id)
    if not promo:
        raise HTTPException(status_code=404, detail="Promoción no encontrada.")
    
    p_dict = promo.model_dump()
    p_dict["producto_ids"] = [
        pp.producto_id for pp in db.exec(select(PromocionProducto).where(PromocionProducto.promocion_id == promo.id)).all()
    ]
    p_dict["categoria_ids"] = [
        pc.categoria_id for pc in db.exec(select(PromocionCategoria).where(PromocionCategoria.promocion_id == promo.id)).all()
    ]
    return p_dict


@router.post("/", response_model=PromocionResponse, status_code=201)
def crear_promocion(
    payload: PromocionCreate,
    db: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    info = verificar_rol_empleado(token_obj.credentials, ["ADMIN", "GERENTE"], db)

    existente = db.exec(select(Promocion).where(Promocion.nombre == payload.nombre)).first()
    if existente:
        raise HTTPException(status_code=400, detail=f"Ya existe una promoción con el nombre '{payload.nombre}'.")

    promo_data = payload.model_dump(exclude={"producto_ids", "categoria_ids"})
    promo = Promocion(**promo_data)
    db.add(promo)
    db.flush()

    if payload.aplica_a == "PRODUCTOS" and payload.producto_ids:
        for pid in payload.producto_ids:
            producto = db.get(Producto, pid)
            if not producto or not producto.activo:
                raise HTTPException(status_code=404, detail=f"Producto id={pid} no encontrado o inactivo.")
            db.add(PromocionProducto(promocion_id=promo.id, producto_id=pid))

    if payload.aplica_a == "CATEGORIAS" and payload.categoria_ids:
        for cid in payload.categoria_ids:
            cat = db.get(Categoria, cid)
            if not cat or not cat.activo:
                raise HTTPException(status_code=404, detail=f"Categoría id={cid} no encontrada o inactiva.")
            db.add(PromocionCategoria(promocion_id=promo.id, categoria_id=cid))

    db.commit()
    db.refresh(promo)

    log_auditoria(
        nivel="INFO",
        origen="POST /api/v1/promociones",
        mensaje=f"Promoción creada: '{promo.nombre}' (id={promo.id}) por empleado_id={info['empleado_id']}",
    )
    p_dict = promo.model_dump()
    p_dict["producto_ids"] = [
        pp.producto_id for pp in db.exec(select(PromocionProducto).where(PromocionProducto.promocion_id == promo.id)).all()
    ]
    p_dict["categoria_ids"] = [
        pc.categoria_id for pc in db.exec(select(PromocionCategoria).where(PromocionCategoria.promocion_id == promo.id)).all()
    ]
    return p_dict


@router.put("/{promocion_id}", response_model=PromocionResponse)
def actualizar_promocion(
    promocion_id: int,
    payload: PromocionUpdate,
    db: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    info = verificar_rol_empleado(token_obj.credentials, ["ADMIN", "GERENTE"], db)

    promo = db.get(Promocion, promocion_id)
    if not promo:
        raise HTTPException(status_code=404, detail="Promoción no encontrada.")

    datos = payload.model_dump(exclude_unset=True, exclude={"producto_ids", "categoria_ids"})

    if "nombre" in datos:
        dup = db.exec(
            select(Promocion).where(
                Promocion.nombre == datos["nombre"],
                col(Promocion.id) != promocion_id
            )
        ).first()
        if dup:
            raise HTTPException(status_code=400, detail=f"Ya existe otra promoción con el nombre '{datos['nombre']}'.")

    for campo, valor in datos.items():
        setattr(promo, campo, valor)

    aplica_a = getattr(payload, 'aplica_a', None) or promo.aplica_a

    if payload.producto_ids is not None:
        db.exec(select(PromocionProducto).where(PromocionProducto.promocion_id == promocion_id))
        for pp in db.exec(select(PromocionProducto).where(PromocionProducto.promocion_id == promocion_id)).all():
            db.delete(pp)
        for pid in payload.producto_ids:
            producto = db.get(Producto, pid)
            if not producto or not producto.activo:
                raise HTTPException(status_code=404, detail=f"Producto id={pid} no encontrado o inactivo.")
            db.add(PromocionProducto(promocion_id=promocion_id, producto_id=pid))

    if payload.categoria_ids is not None:
        for pc in db.exec(select(PromocionCategoria).where(PromocionCategoria.promocion_id == promocion_id)).all():
            db.delete(pc)
        for cid in payload.categoria_ids:
            cat = db.get(Categoria, cid)
            if not cat or not cat.activo:
                raise HTTPException(status_code=404, detail=f"Categoría id={cid} no encontrada o inactiva.")
            db.add(PromocionCategoria(promocion_id=promocion_id, categoria_id=cid))

    db.add(promo)
    db.commit()
    db.refresh(promo)

    log_auditoria(
        nivel="INFO",
        origen=f"PUT /api/v1/promociones/{promocion_id}",
        mensaje=f"Promoción actualizada: id={promocion_id} por empleado_id={info['empleado_id']}",
    )
    p_dict = promo.model_dump()
    p_dict["producto_ids"] = [
        pp.producto_id for pp in db.exec(select(PromocionProducto).where(PromocionProducto.promocion_id == promo.id)).all()
    ]
    p_dict["categoria_ids"] = [
        pc.categoria_id for pc in db.exec(select(PromocionCategoria).where(PromocionCategoria.promocion_id == promo.id)).all()
    ]
    return p_dict


@router.delete("/{promocion_id}", response_model=dict)
def desactivar_promocion(
    promocion_id: int,
    db: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    info = verificar_rol_empleado(token_obj.credentials, ["ADMIN", "GERENTE"], db)

    promo = db.get(Promocion, promocion_id)
    if not promo:
        raise HTTPException(status_code=404, detail="Promoción no encontrada.")
    if not promo.activo:
        raise HTTPException(status_code=400, detail="La promoción ya está inactiva.")

    promo.activo = False
    db.add(promo)
    db.commit()

    log_auditoria(
        nivel="WARNING",
        origen=f"DELETE /api/v1/promociones/{promocion_id}",
        mensaje=f"Promoción desactivada: id={promocion_id}, nombre='{promo.nombre}'",
    )
    return {"mensaje": f"Promoción '{promo.nombre}' desactivada.", "id": promocion_id}


@router.get("/evaluar/item", response_model=List[PromocionAplicadaResponse])
def evaluar_promociones_item(
    producto_id: int = Query(...),
    categoria_id: int = Query(...),
    subtotal: float = Query(..., gt=0),
    db: Session = Depends(get_session)
):
    return evaluar_promociones_para_item(
        session=db,
        producto_id=producto_id,
        categoria_id=categoria_id,
        subtotal_linea=Decimal(str(subtotal))
    )


@router.get("/evaluar/mejor-descuento", response_model=Optional[PromocionAplicadaResponse])
def evaluar_mejor_descuento(
    producto_id: int = Query(...),
    categoria_id: int = Query(...),
    subtotal: float = Query(..., gt=0),
    db: Session = Depends(get_session)
):
    return obtener_mejor_promocion(
        session=db,
        producto_id=producto_id,
        categoria_id=categoria_id,
        subtotal_linea=Decimal(str(subtotal))
    )


@router.get("/evaluar/globales", response_model=List[PromocionAplicadaResponse])
def evaluar_descuentos_globales(
    subtotal_total: float = Query(..., gt=0, description="Total del pedido sobre el cual se aplican descuentos globales"),
    db: Session = Depends(get_session)
):
    return evaluar_promociones_globales(
        session=db,
        subtotal_total=Decimal(str(subtotal_total))
    )


@router.get("/happy-hour/activo", response_model=dict)
def verificar_happy_hour_activo(db: Session = Depends(get_session)):

    ahora = get_local_now()
    stmt = select(Promocion).where(
        col(Promocion.activo) == True,
        col(Promocion.aplica_happy_hour) == True
    )
    promociones_hh = db.exec(stmt).all()

    activas_ahora = []
    for promo in promociones_hh:
        if _promocion_vigente(promo, ahora) and _es_happy_hour(promo, ahora):
            activas_ahora.append({
                "id": promo.id,
                "nombre": promo.nombre,
                "tipo_descuento": promo.tipo_descuento,
                "valor": float(promo.valor),
                "hora_inicio": promo.hora_inicio_hh,
                "hora_fin": promo.hora_fin_hh,
            })

    return {
        "happy_hour_activo": len(activas_ahora) > 0,
        "hora_actual": ahora.strftime("%H:%M"),
        "promociones_activas": activas_ahora
    }


@router.patch("/{promocion_id}/reactivar", response_model=dict)
def reactivar_promocion(
    promocion_id: int,
    db: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    info = verificar_rol_empleado(token_obj.credentials, ["ADMIN", "GERENTE"], db)

    promo = db.get(Promocion, promocion_id)
    if not promo:
        raise HTTPException(status_code=404, detail="Promoción no encontrada.")
    if promo.activo:
        raise HTTPException(status_code=400, detail="La promoción ya está activa.")

    promo.activo = True
    db.add(promo)
    db.commit()

    log_auditoria(
        nivel="INFO",
        origen=f"PATCH /api/v1/promociones/{promocion_id}/reactivar",
        mensaje=f"Promoción reactivada: id={promocion_id}, nombre='{promo.nombre}'",
    )
    return {"mensaje": f"Promoción '{promo.nombre}' reactivada.", "id": promocion_id}





class SupervisorAuthRequest(BaseModel):
    email: str
    otp: str

@router.post("/supervisor/auth")
def auth_supervisor(payload: SupervisorAuthRequest, db: Session = Depends(get_session)):
    from app.services.totp_service import verificar_supervisor_totp
    try:
        sup = verificar_supervisor_totp(db, payload.email, payload.otp)
        return {"ok": True, "supervisor_id": sup["supervisor_id"], "supervisor_nombre": sup["supervisor_nombre"]}
    except HTTPException as e:
        return {"ok": False, "error": e.detail}


@router.post("/supervisor/sessions/sync", response_model=dict)
def sync_supervisor_sessions(
    payload: List[SupervisorSessionSync],
    db: Session = Depends(get_session)
):
    from app.models.core_models import SupervisorSessionAudit
    import uuid
    for s in payload:
        record_id = s.id
        if not record_id:
            record_id = uuid.uuid4()
        audit = SupervisorSessionAudit(
            id=record_id,
            supervisor_id=s.supervisor_id,
            cajero_id=s.cajero_id,
            terminal=s.terminal,
            inicio=s.inicio,
            fin=s.fin,
            motivo_fin=s.motivo_fin
        )
        db.add(audit)
    db.commit()
    return {"mensaje": "Sincronización completada."}
