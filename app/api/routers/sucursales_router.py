from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials
from sqlmodel import Session, select, col
from datetime import datetime

from app.db.database import get_session
from app.models.core_models import Sucursal
from app.schemas.sucursales_schema import SucursalCreate, SucursalUpdate, SucursalResponse
from app.services.audit_service import log_auditoria
from app.core.security import oauth2_scheme, verificar_rol_empleado, security_bearer

router = APIRouter(prefix="/api/v1/sucursales", tags=["Catálogos"])


@router.get("/", response_model=List[SucursalResponse])
def obtener_sucursales(
    incluir_inactivas: bool = Query(False, description="Incluir sucursales inactivas"),
    db: Session = Depends(get_session)
):
    stmt = select(Sucursal)
    if not incluir_inactivas:
        stmt = stmt.where(col(Sucursal.activo) == True)
    sucursales = db.exec(stmt).all()
    return sucursales


@router.get("/{sucursal_id}", response_model=SucursalResponse)
def obtener_sucursal(
    sucursal_id: int,
    db: Session = Depends(get_session)
):
    sucursal = db.get(Sucursal, sucursal_id)
    if not sucursal:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada.")
    return sucursal


@router.post("/", response_model=SucursalResponse, status_code=201)
def crear_sucursal(
    payload: SucursalCreate,
    db: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    verificar_rol_empleado(token_obj.credentials, ["ADMIN", "GERENTE"], db)

    existente = db.exec(select(Sucursal).where(Sucursal.nombre == payload.nombre)).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe una sucursal con ese nombre.")

    sucursal = Sucursal(nombre=payload.nombre, direccion=payload.direccion, activo=True)
    db.add(sucursal)
    db.commit()
    db.refresh(sucursal)

    log_auditoria(
        nivel="INFO",
        origen="POST /api/v1/sucursales",
        mensaje=f"Sucursal creada: '{sucursal.nombre}' (id={sucursal.id})",
    )
    return sucursal


@router.put("/{sucursal_id}", response_model=SucursalResponse)
def actualizar_sucursal(
    sucursal_id: int,
    payload: SucursalUpdate,
    db: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    verificar_rol_empleado(token_obj.credentials, ["ADMIN", "GERENTE"], db)

    sucursal = db.get(Sucursal, sucursal_id)
    if not sucursal:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada.")

    datos = payload.model_dump(exclude_unset=True)

    if "nombre" in datos and datos["nombre"]:
        # Verificar nombre único
        existente = db.exec(
            select(Sucursal).where(
                Sucursal.nombre == datos["nombre"],
                col(Sucursal.id) != sucursal_id
            )
        ).first()
        if existente:
            raise HTTPException(status_code=400, detail="Ya existe una sucursal con ese nombre.")

    for campo, valor in datos.items():
        setattr(sucursal, campo, valor)

    db.add(sucursal)
    db.commit()
    db.refresh(sucursal)

    log_auditoria(
        nivel="INFO",
        origen=f"PUT /api/v1/sucursales/{sucursal_id}",
        mensaje=f"Sucursal actualizada: id={sucursal_id}",
        data=datos
    )
    return sucursal


@router.delete("/{sucursal_id}", response_model=dict)
def desactivar_sucursal(
    sucursal_id: int,
    db: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    verificar_rol_empleado(token_obj.credentials, ["ADMIN"], db)

    sucursal = db.get(Sucursal, sucursal_id)
    if not sucursal:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada.")
    if not sucursal.activo:
        raise HTTPException(status_code=400, detail="La sucursal ya está inactiva.")

    sucursal.activo = False
    db.add(sucursal)
    db.commit()

    log_auditoria(
        nivel="WARNING",
        origen=f"DELETE /api/v1/sucursales/{sucursal_id}",
        mensaje=f"Sucursal desactivada: id={sucursal_id}, nombre='{sucursal.nombre}'",
    )
    return {"mensaje": f"Sucursal '{sucursal.nombre}' desactivada exitosamente.", "id": sucursal_id}