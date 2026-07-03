from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials
from sqlmodel import Session, select, col, or_

from app.db.database import get_session
from app.models.core_models import Cliente
from app.schemas.clientes_schema import ClienteAdminResponse, ClienteListResponse, ClienteEstadoResponse
from app.services.audit_service import log_auditoria
from app.core.security import verificar_rol_empleado, security_bearer

router = APIRouter(prefix="/api/v1/admin/clientes", tags=["Administración de Clientes Móvil"])


@router.get("/", response_model=ClienteListResponse)
def listar_clientes(
    busqueda: Optional[str] = Query(None, description="Buscar por nombre, email o teléfono"),
    solo_activos: bool = Query(True, description="Filtrar solo clientes activos"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    verificar_rol_empleado(token_obj.credentials if token_obj else None, ["ADMIN", "GERENTE", "CAJERO"], db)

    stmt = select(Cliente)

    if solo_activos:
        stmt = stmt.where(col(Cliente.activo) == True)

    if busqueda:
        patron = f"%{busqueda}%"
        stmt = stmt.where(
            or_(
                col(Cliente.nombre_completo).like(patron),
                col(Cliente.email).like(patron),
                col(Cliente.telefono).like(patron),
            )
        )

    total_stmt = stmt
    todos = db.exec(total_stmt).all()
    total = len(todos)

    stmt = stmt.order_by(col(Cliente.id)).offset(skip).limit(limit)
    clientes = db.exec(stmt).all()

    return ClienteListResponse(total=total, clientes=clientes)


@router.get("/{cliente_id}", response_model=ClienteAdminResponse)
def obtener_cliente(
    cliente_id: int,
    db: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    verificar_rol_empleado(token_obj.credentials if token_obj else None, ["ADMIN", "GERENTE", "CAJERO"], db)

    cliente = db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")
    return cliente


@router.post("/{cliente_id}/desactivar", response_model=ClienteEstadoResponse)
def desactivar_cliente(
    cliente_id: int,
    db: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    info = verificar_rol_empleado(token_obj.credentials if token_obj else None, ["ADMIN", "GERENTE"], db)

    cliente = db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")
    if not cliente.activo:
        raise HTTPException(status_code=400, detail="El cliente ya está inactivo.")

    cliente.activo = False
    db.add(cliente)
    db.commit()

    log_auditoria(
        nivel="WARNING",
        origen=f"POST /api/v1/admin/clientes/{cliente_id}/desactivar",
        mensaje=f"Cliente desactivado: id={cliente_id}, email='{cliente.email}' por empleado_id={info['empleado_id']}",
    )

    return ClienteEstadoResponse(
        mensaje=f"Cliente '{cliente.nombre_completo}' desactivado. La cuenta móvil ha sido bloqueada.",
        cliente_id=cliente_id,
        activo=False
    )


@router.post("/{cliente_id}/reactivar", response_model=ClienteEstadoResponse)
def reactivar_cliente(
    cliente_id: int,
    db: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    info = verificar_rol_empleado(token_obj.credentials if token_obj else None, ["ADMIN", "GERENTE"], db)

    cliente = db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")
    if cliente.activo:
        raise HTTPException(status_code=400, detail="El cliente ya está activo.")

    cliente.activo = True
    db.add(cliente)
    db.commit()

    log_auditoria(
        nivel="INFO",
        origen=f"POST /api/v1/admin/clientes/{cliente_id}/reactivar",
        mensaje=f"Cliente reactivado: id={cliente_id}, email='{cliente.email}' por empleado_id={info['empleado_id']}",
    )

    return ClienteEstadoResponse(
        mensaje=f"Cliente '{cliente.nombre_completo}' reactivado exitosamente.",
        cliente_id=cliente_id,
        activo=True
    )
