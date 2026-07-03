"""
Servicio de Secuencias NCF.
Maneja la asignación automática y administración de comprobantes fiscales (NCF).
Bloquea cuando no hay secuencias disponibles o están vencidas.
"""
from datetime import datetime, timezone
from sqlmodel import Session, select
from fastapi import HTTPException

from app.models.core_models import SecuenciaNcf, HistorialNcf
from app.services.audit_service import log_auditoria
from app.core.timezone import get_local_now


# Tipos de NCF válidos en República Dominicana
TIPOS_NCF = {
    "B01": "Crédito Fiscal",
    "B02": "Consumidor Final",
    "B14": "Régimen Especial",
    "B15": "Gubernamental",
    "B16": "Exportaciones",
}


def _formatear_ncf(tipo_ncf: str, serie: str, secuencia: int) -> str:
    """Formatea el NCF completo: B02-SERIE-00000001"""
    return f"{tipo_ncf}-{serie}-{str(secuencia).zfill(8)}"


def obtener_secuencia_activa(
    session: Session,
    tipo_ncf: str,
    sucursal_id: int = None
) -> SecuenciaNcf:
    """
    Obtiene la secuencia NCF activa y válida para el tipo dado.
    Lanza HTTPException si no hay secuencia disponible.
    """
    now = get_local_now()

    stmt = select(SecuenciaNcf).where(
        SecuenciaNcf.tipo_ncf == tipo_ncf,
        SecuenciaNcf.activo == True,
        SecuenciaNcf.fecha_vencimiento > now,
    )

    if sucursal_id is not None:
        stmt = stmt.where(SecuenciaNcf.sucursal_id == sucursal_id)

    stmt = stmt.order_by(SecuenciaNcf.id.asc())
    secuencia = session.exec(stmt).first()

    if not secuencia:
        log_auditoria(
            nivel="CRITICAL",
            origen="NCFService",
            mensaje=f"No hay secuencia NCF activa para tipo={tipo_ncf}, sucursal={sucursal_id}",
        )
        raise HTTPException(
            status_code=409,
            detail=(
                f"No existe una secuencia NCF activa y vigente para el tipo '{tipo_ncf}'. "
                "Contacte al administrador para cargar rangos autorizados."
            )
        )

    # Verificar que no esté agotada
    if secuencia.secuencia_actual > secuencia.rango_hasta:
        secuencia.activo = False
        session.add(secuencia)
        session.flush()
        log_auditoria(
            nivel="WARNING",
            origen="NCFService",
            mensaje=f"Secuencia NCF id={secuencia.id} agotada y desactivada automáticamente.",
        )
        raise HTTPException(
            status_code=409,
            detail="La secuencia NCF se ha agotado. Se requiere cargar un nuevo rango autorizado."
        )

    return secuencia


def asignar_ncf(
    session: Session,
    tipo_ncf: str,
    pedido_id: int = None,
    empleado_id: int = None,
    sucursal_id: int = None,
) -> dict:
    """
    Asigna automáticamente el siguiente NCF disponible.
    Registra el historial y avanza la secuencia.
    Retorna dict con el NCF asignado y metadata.
    """
    secuencia = obtener_secuencia_activa(session, tipo_ncf, sucursal_id)

    ncf_numero = secuencia.secuencia_actual
    ncf_completo = _formatear_ncf(secuencia.tipo_ncf, secuencia.serie, ncf_numero)

    # Avanzar secuencia
    secuencia.secuencia_actual += 1

    # Si se agota, desactivar automáticamente
    if secuencia.secuencia_actual > secuencia.rango_hasta:
        secuencia.activo = False
        log_auditoria(
            nivel="WARNING",
            origen="NCFService",
            mensaje=f"Secuencia NCF id={secuencia.id} agotada luego de asignar {ncf_completo}.",
        )

    session.add(secuencia)

    # Registrar historial
    historial = HistorialNcf(
        secuencia_id=secuencia.id,
        ncf_asignado=ncf_completo,
        pedido_id=pedido_id,
        empleado_id=empleado_id,
    )
    session.add(historial)
    session.flush()

    log_auditoria(
        nivel="INFO",
        origen="NCFService",
        mensaje=f"NCF asignado: {ncf_completo}",
        data={"ncf": ncf_completo, "pedido_id": pedido_id, "empleado_id": empleado_id}
    )

    return {
        "ncf_asignado": ncf_completo,
        "tipo_ncf": secuencia.tipo_ncf,
        "serie": secuencia.serie,
        "secuencia_id": secuencia.id,
        "pedido_id": pedido_id,
        "fecha_asignacion": historial.fecha_asignacion or get_local_now(),
    }


def verificar_disponibilidad_ncf(
    session: Session,
    tipo_ncf: str,
    sucursal_id: int = None,
) -> dict:
    """
    Verifica cuántos NCF quedan disponibles para un tipo dado.
    No asigna ninguno, solo informa.
    """
    now = get_local_now()

    stmt = select(SecuenciaNcf).where(
        SecuenciaNcf.tipo_ncf == tipo_ncf,
        SecuenciaNcf.activo == True,
        SecuenciaNcf.fecha_vencimiento > now,
    )
    if sucursal_id is not None:
        stmt = stmt.where(SecuenciaNcf.sucursal_id == sucursal_id)

    secuencia = session.exec(stmt).first()

    if not secuencia:
        return {
            "disponibles": 0,
            "estado": "SIN_SECUENCIA",
            "mensaje": "No hay secuencia activa para este tipo.",
        }

    disponibles = max(0, secuencia.rango_hasta - secuencia.secuencia_actual + 1)
    total = secuencia.rango_hasta - secuencia.rango_desde + 1
    porcentaje_uso = round(((total - disponibles) / total) * 100, 2) if total > 0 else 0

    estado = "OK"
    if disponibles == 0:
        estado = "AGOTADA"
    elif disponibles < 50:
        estado = "CRITICO"
    elif disponibles < 200:
        estado = "BAJO"

    return {
        "secuencia_id": secuencia.id,
        "tipo_ncf": tipo_ncf,
        "disponibles": disponibles,
        "secuencia_actual": secuencia.secuencia_actual,
        "rango_hasta": secuencia.rango_hasta,
        "fecha_vencimiento": secuencia.fecha_vencimiento,
        "porcentaje_uso": porcentaje_uso,
        "estado": estado,
    }
