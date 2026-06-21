from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, col
from decimal import Decimal
from datetime import datetime

from app.db.database import get_session
from app.models.core_models import Promocion, PromocionProducto, PromocionCategoria, Producto, Categoria
from app.schemas.promociones_schema import (
    PromocionCreate, PromocionUpdate, PromocionResponse, PromocionAplicadaResponse
)
from app.services.audit_service import log_auditoria
from app.services.promociones_service import (
    evaluar_promociones_para_item, obtener_mejor_promocion, evaluar_promociones_globales
)
from app.core.security import oauth2_scheme, verificar_rol_empleado

router = APIRouter(prefix="/api/v1/promociones", tags=["Promociones y Descuentos"])


# ─── CRUD ───────────────────────────────────────────────────────────

@router.get("/", response_model=List[PromocionResponse])
def listar_promociones(
    solo_activas: bool = Query(True),
    db: Session = Depends(get_session)
):
    stmt = select(Promocion)
    if solo_activas:
        stmt = stmt.where(col(Promocion.activo) == True)
    stmt = stmt.order_by(Promocion.prioridad.desc())
    return db.exec(stmt).all()


@router.get("/{promocion_id}", response_model=PromocionResponse)
def obtener_promocion(promocion_id: int, db: Session = Depends(get_session)):
    promo = db.get(Promocion, promocion_id)
    if not promo:
        raise HTTPException(status_code=404, detail="Promoción no encontrada.")
    return promo


@router.post("/", response_model=PromocionResponse, status_code=201)
def crear_promocion(
    payload: PromocionCreate,
    db: Session = Depends(get_session),
    token: Optional[str] = Depends(oauth2_scheme)
):
    info = verificar_rol_empleado(token, ["ADMIN", "GERENTE"], db)

    existente = db.exec(select(Promocion).where(Promocion.nombre == payload.nombre)).first()
    if existente:
        raise HTTPException(status_code=400, detail=f"Ya existe una promoción con el nombre '{payload.nombre}'.")

    promo_data = payload.model_dump(exclude={"producto_ids", "categoria_ids"})
    promo = Promocion(**promo_data)
    db.add(promo)
    db.flush()

    # Asociar productos si aplica
    if payload.aplica_a == "PRODUCTOS" and payload.producto_ids:
        for pid in payload.producto_ids:
            producto = db.get(Producto, pid)
            if not producto:
                raise HTTPException(status_code=404, detail=f"Producto id={pid} no encontrado.")
            db.add(PromocionProducto(promocion_id=promo.id, producto_id=pid))

    # Asociar categorías si aplica
    if payload.aplica_a == "CATEGORIAS" and payload.categoria_ids:
        for cid in payload.categoria_ids:
            cat = db.get(Categoria, cid)
            if not cat:
                raise HTTPException(status_code=404, detail=f"Categoría id={cid} no encontrada.")
            db.add(PromocionCategoria(promocion_id=promo.id, categoria_id=cid))

    db.commit()
    db.refresh(promo)

    log_auditoria(
        nivel="INFO",
        origen="POST /api/v1/promociones",
        mensaje=f"Promoción creada: '{promo.nombre}' (id={promo.id}) por empleado_id={info['empleado_id']}",
    )
    return promo


@router.put("/{promocion_id}", response_model=PromocionResponse)
def actualizar_promocion(
    promocion_id: int,
    payload: PromocionUpdate,
    db: Session = Depends(get_session),
    token: Optional[str] = Depends(oauth2_scheme)
):
    info = verificar_rol_empleado(token, ["ADMIN", "GERENTE"], db)

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

    # Actualizar asociaciones si se envían
    aplica_a = getattr(payload, 'aplica_a', None) or promo.aplica_a

    if payload.producto_ids is not None:
        db.exec(select(PromocionProducto).where(PromocionProducto.promocion_id == promocion_id))
        for pp in db.exec(select(PromocionProducto).where(PromocionProducto.promocion_id == promocion_id)).all():
            db.delete(pp)
        for pid in payload.producto_ids:
            db.add(PromocionProducto(promocion_id=promocion_id, producto_id=pid))

    if payload.categoria_ids is not None:
        for pc in db.exec(select(PromocionCategoria).where(PromocionCategoria.promocion_id == promocion_id)).all():
            db.delete(pc)
        for cid in payload.categoria_ids:
            db.add(PromocionCategoria(promocion_id=promocion_id, categoria_id=cid))

    db.add(promo)
    db.commit()
    db.refresh(promo)

    log_auditoria(
        nivel="INFO",
        origen=f"PUT /api/v1/promociones/{promocion_id}",
        mensaje=f"Promoción actualizada: id={promocion_id} por empleado_id={info['empleado_id']}",
    )
    return promo


@router.delete("/{promocion_id}", response_model=dict)
def desactivar_promocion(
    promocion_id: int,
    db: Session = Depends(get_session),
    token: Optional[str] = Depends(oauth2_scheme)
):
    info = verificar_rol_empleado(token, ["ADMIN", "GERENTE"], db)

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


# ─── Endpoints de Evaluación ──────────────────────────────────────────────

@router.get("/evaluar/item", response_model=List[PromocionAplicadaResponse])
def evaluar_promociones_item(
    producto_id: int = Query(...),
    categoria_id: int = Query(...),
    subtotal: float = Query(..., gt=0),
    db: Session = Depends(get_session)
):
    """
    Evaluar qué promociones aplican a un producto específico en este momento.
    Incluye validación de Happy Hour.
    """
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
    """Retorna únicamente la mejor promoción (mayor descuento) para un ítem."""
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
    """Evaluar descuentos globales (aplica_a=TODOS) sobre el total del pedido."""
    return evaluar_promociones_globales(
        session=db,
        subtotal_total=Decimal(str(subtotal_total))
    )


@router.get("/happy-hour/activo", response_model=dict)
def verificar_happy_hour_activo(db: Session = Depends(get_session)):
    """Verifica si hay alguna promoción de Happy Hour activa en este momento."""
    from app.services.promociones_service import _es_happy_hour, _promocion_vigente
    from datetime import datetime, timezone

    ahora = datetime.now(timezone.utc).replace(tzinfo=None)
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
