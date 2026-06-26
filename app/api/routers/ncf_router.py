from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, col

from app.db.database import get_session
from app.models.core_models import SecuenciaNcf, HistorialNcf
from app.schemas.ncf_schema import (
    SecuenciaNcfCreate, SecuenciaNcfUpdate, SecuenciaNcfResponse,
    NcfAsignacionRequest, NcfAsignadoResponse, HistorialNcfResponse
)
from app.services.ncf_service import asignar_ncf, verificar_disponibilidad_ncf, TIPOS_NCF
from app.services.audit_service import log_auditoria
from app.core.security import oauth2_scheme, verificar_rol_empleado

router = APIRouter(prefix="/api/v1/ncf", tags=["Secuencias NCF"])


def _to_response(seq: SecuenciaNcf) -> dict:
    total = seq.rango_hasta - seq.rango_desde + 1
    disponibles = max(0, seq.rango_hasta - seq.secuencia_actual + 1)
    porcentaje_uso = round(((total - disponibles) / total) * 100, 2) if total > 0 else 0
    return {
        "id": seq.id,
        "tipo_ncf": seq.tipo_ncf,
        "serie": seq.serie,
        "rango_desde": seq.rango_desde,
        "rango_hasta": seq.rango_hasta,
        "secuencia_actual": seq.secuencia_actual,
        "fecha_vencimiento": seq.fecha_vencimiento,
        "activo": seq.activo,
        "sucursal_id": seq.sucursal_id,
        "fecha_creacion": seq.fecha_creacion,
        "disponibles": disponibles,
        "porcentaje_uso": porcentaje_uso,
    }


# ─── Administración de Secuencias ────────────────────────────────────────────

@router.get("/secuencias", response_model=List[SecuenciaNcfResponse])
def listar_secuencias(
    solo_activas: bool = Query(True),
    tipo_ncf: Optional[str] = Query(None),
    sucursal_id: Optional[int] = Query(None),
    db: Session = Depends(get_session),
    token: Optional[str] = Depends(oauth2_scheme)
):
    verificar_rol_empleado(token, ["ADMIN", "GERENTE", "CAJERO"], db)

    stmt = select(SecuenciaNcf)
    if solo_activas:
        stmt = stmt.where(col(SecuenciaNcf.activo) == True)
    if tipo_ncf:
        stmt = stmt.where(col(SecuenciaNcf.tipo_ncf) == tipo_ncf)
    if sucursal_id:
        stmt = stmt.where(col(SecuenciaNcf.sucursal_id) == sucursal_id)

    secuencias = db.exec(stmt).all()
    return [_to_response(s) for s in secuencias]


@router.get("/secuencias/{secuencia_id}", response_model=SecuenciaNcfResponse)
def obtener_secuencia(
    secuencia_id: int,
    db: Session = Depends(get_session),
    token: Optional[str] = Depends(oauth2_scheme)
):
    verificar_rol_empleado(token, ["ADMIN", "GERENTE", "CAJERO"], db)
    seq = db.get(SecuenciaNcf, secuencia_id)
    if not seq:
        raise HTTPException(status_code=404, detail="Secuencia NCF no encontrada.")
    return _to_response(seq)


@router.post("/secuencias", response_model=SecuenciaNcfResponse, status_code=201)
def crear_secuencia(
    payload: SecuenciaNcfCreate,
    db: Session = Depends(get_session),
    token: Optional[str] = Depends(oauth2_scheme)
):
    info = verificar_rol_empleado(token, ["ADMIN"], db)

    seq = SecuenciaNcf(
        tipo_ncf=payload.tipo_ncf,
        serie=payload.serie,
        rango_desde=payload.rango_desde,
        rango_hasta=payload.rango_hasta,
        secuencia_actual=payload.rango_desde,
        fecha_vencimiento=payload.fecha_vencimiento,
        activo=True,
        sucursal_id=payload.sucursal_id,
    )
    db.add(seq)
    db.commit()
    db.refresh(seq)

    log_auditoria(
        nivel="INFO",
        origen="POST /api/v1/ncf/secuencias",
        mensaje=f"Secuencia NCF creada: tipo={seq.tipo_ncf}, rango={seq.rango_desde}-{seq.rango_hasta}, id={seq.id}",
        data={"admin_id": info["empleado_id"]}
    )
    return _to_response(seq)


@router.put("/secuencias/{secuencia_id}", response_model=SecuenciaNcfResponse)
def actualizar_secuencia(
    secuencia_id: int,
    payload: SecuenciaNcfUpdate,
    db: Session = Depends(get_session),
    token: Optional[str] = Depends(oauth2_scheme)
):
    info = verificar_rol_empleado(token, ["ADMIN"], db)

    seq = db.get(SecuenciaNcf, secuencia_id)
    if not seq:
        raise HTTPException(status_code=404, detail="Secuencia NCF no encontrada.")

    datos = payload.model_dump(exclude_unset=True)
    for campo, valor in datos.items():
        setattr(seq, campo, valor)

    db.add(seq)
    db.commit()
    db.refresh(seq)

    log_auditoria(
        nivel="INFO",
        origen=f"PUT /api/v1/ncf/secuencias/{secuencia_id}",
        mensaje=f"Secuencia NCF actualizada: id={secuencia_id}",
        data=datos
    )
    return _to_response(seq)


# ─── Asignación automática de NCF ───────────────────────────────────────────

@router.post("/asignar", response_model=NcfAsignadoResponse)
def asignar_ncf_endpoint(
    payload: NcfAsignacionRequest,
    db: Session = Depends(get_session),
    token: Optional[str] = Depends(oauth2_scheme)
):
    """
    Asigna automáticamente el siguiente NCF disponible.
    Bloquea si no hay secuencia activa o si está agotada.
    """
    verificar_rol_empleado(token, ["ADMIN", "GERENTE", "CAJERO"], db)

    resultado = asignar_ncf(
        session=db,
        tipo_ncf=payload.tipo_ncf,
        pedido_id=payload.pedido_id,
        empleado_id=payload.empleado_id,
        sucursal_id=payload.sucursal_id,
    )
    db.commit()
    return resultado


# ─── Disponibilidad y estado ─────────────────────────────────────────────────────

@router.get("/disponibilidad", response_model=dict)
def verificar_disponibilidad(
    tipo_ncf: str = Query("B02"),
    sucursal_id: Optional[int] = Query(None),
    db: Session = Depends(get_session),
    token: Optional[str] = Depends(oauth2_scheme)
):
    """Verifica cuántos NCF quedan disponibles sin asignar ninguno."""
    verificar_rol_empleado(token, ["ADMIN", "GERENTE", "CAJERO"], db)
    return verificar_disponibilidad_ncf(db, tipo_ncf, sucursal_id)


# ─── Historial ──────────────────────────────────────────────────────────────────────────────

@router.get("/historial", response_model=List[HistorialNcfResponse])
def obtener_historial(
    secuencia_id: Optional[int] = Query(None),
    pedido_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_session),
    token: Optional[str] = Depends(oauth2_scheme)
):
    verificar_rol_empleado(token, ["ADMIN", "GERENTE"], db)

    stmt = select(HistorialNcf)
    if secuencia_id:
        stmt = stmt.where(col(HistorialNcf.secuencia_id) == secuencia_id)
    if pedido_id:
        stmt = stmt.where(col(HistorialNcf.pedido_id) == pedido_id)

    stmt = stmt.order_by(HistorialNcf.id.desc()).offset(skip).limit(limit)
    return db.exec(stmt).all()


@router.get("/tipos", response_model=dict)
def listar_tipos_ncf():
    """Lista los tipos de NCF válidos en República Dominicana."""
    return {"tipos": [{"codigo": k, "descripcion": v} for k, v in TIPOS_NCF.items()]}
