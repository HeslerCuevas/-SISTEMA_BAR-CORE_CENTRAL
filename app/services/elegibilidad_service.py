"""
Service for eligibility-based promotions and promo code validation.
Extends the existing promotion engine without modifying it.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List
from sqlmodel import Session, select
from fastapi import HTTPException

from app.models.core_models import (
    Promocion, PromocionElegibilidad, CodigoPromocional, AplicacionPromocion
)
from app.services.promociones_service import _promocion_vigente
from app.core.timezone import get_local_now


def listar_promociones_elegibilidad(db: Session) -> List[dict]:
    """Return all active eligibility promotions with their config."""
    ahora = get_local_now()
    stmt = select(Promocion, PromocionElegibilidad).join(
        PromocionElegibilidad, PromocionElegibilidad.promocion_id == Promocion.id
    ).where(Promocion.activo == True, Promocion.tipo_aplicacion == "ELEGIBILIDAD")
    rows = db.exec(stmt).all()
    result = []
    for promo, eleg in rows:
        if not _promocion_vigente(promo, ahora):
            continue
        result.append({
            "promocion_id": promo.id,
            "nombre": promo.nombre,
            "descripcion": promo.descripcion,
            "tipo_descuento": promo.tipo_descuento,
            "valor": float(promo.valor),
            "etiqueta_identificador": eleg.etiqueta_identificador,
            "requiere_identificador": eleg.requiere_identificador,
            "tipo_aplicacion": promo.tipo_aplicacion,
        })
    return result


def validar_codigo_promocional(
    db: Session,
    codigo: str,
    subtotal: Decimal,
    cliente_id: Optional[int] = None,
) -> dict:
    """
    Validate a promo code. Returns promotion info if valid.
    Raises HTTPException with descriptive message on failure.
    """
    ahora = get_local_now()
    stmt = select(CodigoPromocional).where(
        CodigoPromocional.codigo == codigo.strip().upper(),
        CodigoPromocional.activo == True,
    )
    codigo_obj = db.exec(stmt).first()
    if not codigo_obj:
        raise HTTPException(status_code=404, detail="Código promocional no encontrado o inactivo.")

    if codigo_obj.fecha_fin and codigo_obj.fecha_fin < ahora:
        raise HTTPException(status_code=400, detail="El código promocional ha expirado.")
    if codigo_obj.fecha_inicio > ahora:
        raise HTTPException(status_code=400, detail="El código promocional aún no está vigente.")
    if codigo_obj.uso_maximo is not None and codigo_obj.usos_actuales >= codigo_obj.uso_maximo:
        raise HTTPException(status_code=400, detail="El código promocional ha alcanzado su límite de usos.")
    if codigo_obj.cliente_especifico_id is not None:
        if cliente_id is None or codigo_obj.cliente_especifico_id != cliente_id:
            raise HTTPException(status_code=403, detail="Este código es exclusivo para un cliente específico.")
    if codigo_obj.monto_minimo_compra is not None and subtotal < codigo_obj.monto_minimo_compra:
        raise HTTPException(
            status_code=400,
            detail=f"El monto mínimo de compra para este código es $ {float(codigo_obj.monto_minimo_compra):,.2f}."
        )

    promo = db.get(Promocion, codigo_obj.promocion_id)
    if not promo or not _promocion_vigente(promo, ahora):
        raise HTTPException(status_code=400, detail="La promoción asociada a este código no está vigente.")

    return {
        "valido": True,
        "codigo_id": codigo_obj.id,
        "promocion_id": promo.id,
        "nombre": promo.nombre,
        "tipo_descuento": promo.tipo_descuento,
        "valor": float(promo.valor),
        "tipo_aplicacion": "CODIGO_PROMO",
    }


def redimir_codigo_promocional(db: Session, codigo_id: int) -> None:
    """Atomically increment usage counter. Call after successful sale."""
    codigo_obj = db.get(CodigoPromocional, codigo_id)
    if not codigo_obj:
        return
    codigo_obj.usos_actuales += 1
    db.add(codigo_obj)
    db.commit()


def registrar_aplicacion_promocion(db: Session, payload: dict) -> AplicacionPromocion:
    """Write an immutable audit record for a promotion application."""
    import uuid as _uuid
    factura_uuid = None
    raw = payload.get("factura_uuid")
    if raw:
        try:
            factura_uuid = _uuid.UUID(str(raw))
        except Exception:
            pass

    record = AplicacionPromocion(
        promocion_id=payload.get("promocion_id"),
        nombre_promocion_snap=payload.get("nombre_promocion_snap", ""),
        tipo_aplicacion=payload.get("tipo_aplicacion", "AUTOMATICA"),
        pedido_id=payload.get("pedido_id"),
        factura_uuid=factura_uuid,
        empleado_id=payload.get("empleado_id"),
        empleado_autorizador_id=payload.get("empleado_autorizador_id"),
        cliente_id=payload.get("cliente_id"),
        identificador_capturado=payload.get("identificador_capturado"),
        monto_descuento=Decimal(str(payload.get("monto_descuento", "0"))),
        terminal=payload.get("terminal"),
        notas=payload.get("notas"),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
