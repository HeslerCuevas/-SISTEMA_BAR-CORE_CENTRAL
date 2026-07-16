from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlmodel import Session, select

from app.db.database import get_session
from app.models.core_models import Rol
from app.schemas.roles_schema import RolCreate, RolUpdate, RolResponse
from app.services.audit_service import log_auditoria
from app.core.security import verificar_rol_empleado, security_bearer

router = APIRouter(prefix="/api/v1/roles", tags=["Catálogos"])


@router.get("/", response_model=List[RolResponse])
def obtener_roles(db: Session = Depends(get_session)):
    roles = db.exec(select(Rol)).all()
    return roles


@router.get("/{rol_id}", response_model=RolResponse)
def obtener_rol(rol_id: int, db: Session = Depends(get_session)):
    rol = db.get(Rol, rol_id)
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado.")
    return rol


@router.post("/", response_model=RolResponse, status_code=201)
def crear_rol(
    payload: RolCreate,
    db: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    verificar_rol_empleado(token_obj.credentials, ["ADMIN"], db)

    existente = db.exec(select(Rol).where(Rol.nombre == payload.nombre)).first()
    if existente:
        raise HTTPException(status_code=400, detail=f"A role already exists with the name '{payload.nombre}'.")

    rol = Rol(nombre=payload.nombre)
    db.add(rol)
    db.commit()
    db.refresh(rol)

    log_auditoria(
        nivel="INFO",
        origen="POST /api/v1/roles",
        mensaje=f"Role created: '{rol.nombre}' (id={rol.id})",
    )
    return rol


@router.put("/{rol_id}", response_model=RolResponse)
def actualizar_rol(
    rol_id: int,
    payload: RolUpdate,
    db: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    verificar_rol_empleado(token_obj.credentials, ["ADMIN"], db)

    rol = db.get(Rol, rol_id)
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado.")

    existente = db.exec(
        select(Rol).where(Rol.nombre == payload.nombre)
    ).first()
    if existente and existente.id != rol_id:
        raise HTTPException(status_code=400, detail=f"A role already exists with the name '{payload.nombre}'.")

    nombre_anterior = rol.nombre
    rol.nombre = payload.nombre
    db.add(rol)
    db.commit()
    db.refresh(rol)

    log_auditoria(
        nivel="INFO",
        origen=f"PUT /api/v1/roles/{rol_id}",
        mensaje=f"Role updated: '{nombre_anterior}' -> '{rol.nombre}'",
    )
    return rol