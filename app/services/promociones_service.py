"""
Servicio de Promociones y Happy Hour.
Evalúa y aplica automáticamente descuentos según las reglas configuradas.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from sqlmodel import Session, select

from app.models.core_models import (
    Promocion, PromocionProducto, PromocionCategoria, Producto
)
from app.services.audit_service import log_auditoria


def _hora_en_rango(hora_actual: str, hora_inicio: str, hora_fin: str) -> bool:
    """
    Verifica si una hora (HH:MM) está dentro del rango [inicio, fin].
    Soporta rangos que cruzan medianoche si fin < inicio.
    """
    try:
        h_actual = tuple(int(x) for x in hora_actual.split(":"))
        h_inicio = tuple(int(x) for x in hora_inicio.split(":"))
        h_fin = tuple(int(x) for x in hora_fin.split(":"))

        if h_inicio <= h_fin:
            return h_inicio <= h_actual <= h_fin
        else:
            # Rango cruza medianoche: ej. 22:00 - 02:00
            return h_actual >= h_inicio or h_actual <= h_fin
    except Exception:
        return False


def _promocion_vigente(promocion: Promocion, ahora: datetime) -> bool:
    """Verifica si la promoción está activa y dentro de su rango de fechas."""
    if not promocion.activo:
        return False
    if promocion.fecha_inicio > ahora:
        return False
    if promocion.fecha_fin and promocion.fecha_fin < ahora:
        return False
    return True


def _es_happy_hour(promocion: Promocion, ahora: datetime) -> bool:
    """Verifica si la promoción aplica happy hour en el momento actual."""
    if not promocion.aplica_happy_hour:
        return True  # No tiene restricción de horario
    if not (promocion.hora_inicio_hh and promocion.hora_fin_hh):
        return True

    hora_actual_str = ahora.strftime("%H:%M")
    return _hora_en_rango(hora_actual_str, promocion.hora_inicio_hh, promocion.hora_fin_hh)


def calcular_descuento_promocion(promocion: Promocion, subtotal: Decimal) -> Decimal:
    """Calcula el monto de descuento para una promoción dado un subtotal."""
    if promocion.tipo_descuento == "PORCENTAJE":
        return (subtotal * promocion.valor / Decimal("100")).quantize(Decimal("0.01"))
    elif promocion.tipo_descuento == "MONTO_FIJO":
        return min(promocion.valor, subtotal)
    return Decimal("0.00")


def evaluar_promociones_para_item(
    session: Session,
    producto_id: int,
    categoria_id: int,
    subtotal_linea: Decimal,
) -> List[dict]:
    """
    Evalúa todas las promociones vigentes que aplican a un producto/categoría.
    Retorna lista ordenada por prioridad DESC con los descuentos calculados.
    """
    ahora = datetime.now(timezone.utc).replace(tzinfo=None)

    # Traer todas las promociones activas
    stmt = select(Promocion).where(Promocion.activo == True).order_by(Promocion.prioridad.desc())
    todas = session.exec(stmt).all()

    aplicables = []

    for promo in todas:
        if not _promocion_vigente(promo, ahora):
            continue
        if not _es_happy_hour(promo, ahora):
            continue

        aplica = False

        if promo.aplica_a == "TODOS":
            aplica = True
        elif promo.aplica_a == "PRODUCTOS":
            existe = session.exec(
                select(PromocionProducto).where(
                    PromocionProducto.promocion_id == promo.id,
                    PromocionProducto.producto_id == producto_id
                )
            ).first()
            aplica = existe is not None
        elif promo.aplica_a == "CATEGORIAS":
            existe = session.exec(
                select(PromocionCategoria).where(
                    PromocionCategoria.promocion_id == promo.id,
                    PromocionCategoria.categoria_id == categoria_id
                )
            ).first()
            aplica = existe is not None

        if aplica:
            monto_descuento = calcular_descuento_promocion(promo, subtotal_linea)
            aplicables.append({
                "promocion_id": promo.id,
                "nombre": promo.nombre,
                "tipo_descuento": promo.tipo_descuento,
                "valor": promo.valor,
                "aplica_happy_hour": promo.aplica_happy_hour,
                "monto_descuento_calculado": monto_descuento,
                "prioridad": promo.prioridad,
            })

    return aplicables


def obtener_mejor_promocion(
    session: Session,
    producto_id: int,
    categoria_id: int,
    subtotal_linea: Decimal,
) -> Optional[dict]:
    """
    Obtiene la única mejor promoción (mayor descuento, mayor prioridad).
    Retorna None si no hay promociones aplicables.
    """
    opciones = evaluar_promociones_para_item(
        session, producto_id, categoria_id, subtotal_linea
    )
    if not opciones:
        return None

    # Ordenar por monto de descuento DESC, luego por prioridad DESC
    opciones.sort(key=lambda x: (x["monto_descuento_calculado"], x["prioridad"]), reverse=True)
    return opciones[0]


def evaluar_promociones_globales(
    session: Session,
    subtotal_total: Decimal,
) -> List[dict]:
    """
    Evalúa todas las promociones de tipo TODOS sobre el total de un pedido.
    Útil para descuentos globales.
    """
    ahora = datetime.now(timezone.utc).replace(tzinfo=None)

    stmt = select(Promocion).where(
        Promocion.activo == True,
        Promocion.aplica_a == "TODOS"
    ).order_by(Promocion.prioridad.desc())

    promociones = session.exec(stmt).all()

    resultados = []
    for promo in promociones:
        if not _promocion_vigente(promo, ahora):
            continue
        if not _es_happy_hour(promo, ahora):
            continue

        monto = calcular_descuento_promocion(promo, subtotal_total)
        resultados.append({
            "promocion_id": promo.id,
            "nombre": promo.nombre,
            "tipo_descuento": promo.tipo_descuento,
            "valor": promo.valor,
            "aplica_happy_hour": promo.aplica_happy_hour,
            "monto_descuento_calculado": monto,
            "prioridad": promo.prioridad,
        })

    return resultados
