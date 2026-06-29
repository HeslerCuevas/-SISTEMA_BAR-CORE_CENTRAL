from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials
from sqlmodel import Session, select, col

from app.db.database import get_session
from app.models.core_models import Empleado, Rol, Sucursal
from app.schemas.empleados_schema import EmpleadoCreate, EmpleadoUpdate, EmpleadoAdminResponse, EmpleadoDesactivarResponse, EmpleadoSyncResponse
from app.services.audit_service import log_auditoria
from app.core.security import get_password_hash, oauth2_scheme, verificar_rol_empleado, security_bearer

router = APIRouter(prefix="/api/v1/empleados", tags=["Gestión de Personal"])


from fastapi import Header
import os

@router.get("/sync", response_model=List[EmpleadoSyncResponse])
def sincronizar_empleados_gateway(
    incluir_inactivos: bool = Query(False, description="Incluir empleados inactivos"),
    db: Session = Depends(get_session),
    x_gateway_token: Optional[str] = Header(None)
):
    # Dedicated machine-to-machine endpoint for the Integration Gateway
    gateway_secret = os.getenv("CORE_SECRET_KEY")
    if not x_gateway_token or not gateway_secret or x_gateway_token != gateway_secret:
        raise HTTPException(status_code=403, detail="Acceso denegado. Token de Gateway inválido.")
        
    stmt = select(Empleado)
    if not incluir_inactivos:
        stmt = stmt.where(col(Empleado.activo) == True)
    return db.exec(stmt).all()


@router.get("/", response_model=List[EmpleadoAdminResponse])
def obtener_todos_los_empleados(
    incluir_inactivos: bool = Query(False, description="Incluir empleados inactivos"),
    db: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    if not token_obj:
        raise HTTPException(status_code=401, detail="Token de autenticación requerido.")
    verificar_rol_empleado(token_obj.credentials, ["ADMIN", "GERENTE"], db)
    
    stmt = select(Empleado)
    if not incluir_inactivos:
        stmt = stmt.where(col(Empleado.activo) == True)
    return db.exec(stmt).all()


@router.get("/{empleado_id}", response_model=EmpleadoAdminResponse)
def obtener_empleado(
    empleado_id: int,
    db: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):
    verificar_rol_empleado(token_obj.credentials, ["ADMIN", "GERENTE"], db)
    empleado = db.get(Empleado, empleado_id)
    if not empleado:
        raise HTTPException(status_code=404, detail="Empleado no encontrado.")
    return empleado


@router.post("/", response_model=EmpleadoAdminResponse, status_code=201)
def crear_empleado(
    payload: EmpleadoCreate,
    db: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):

    info = verificar_rol_empleado(token_obj.credentials, ["ADMIN", "GERENTE"], db)

    # Validar email único
    if db.exec(select(Empleado).where(Empleado.email == payload.email)).first():
        raise HTTPException(status_code=400, detail="El email ya está registrado.")

    # Validar documento único
    if db.exec(select(Empleado).where(Empleado.documento_identidad == payload.documento_identidad)).first():
        raise HTTPException(status_code=400, detail="El documento de identidad ya está registrado.")

    # Validar que el rol existe
    rol = db.get(Rol, payload.rol_id)
    if not rol:
        raise HTTPException(status_code=404, detail=f"El rol con id={payload.rol_id} no existe.")

    # Validar que la sucursal existe y está activa
    sucursal = db.get(Sucursal, payload.sucursal_id)
    if not sucursal or not sucursal.activo:
        raise HTTPException(status_code=404, detail=f"La sucursal con id={payload.sucursal_id} no existe o está inactiva.")

    nuevo_empleado = Empleado(
        nombre_completo=payload.nombre_completo,
        documento_identidad=payload.documento_identidad,
        email=payload.email,
        password_hash=get_password_hash(payload.password_plano),
        rol_id=payload.rol_id,
        sucursal_id=payload.sucursal_id,
        activo=True
    )
    db.add(nuevo_empleado)
    db.commit()
    db.refresh(nuevo_empleado)

    log_auditoria(
        nivel="INFO",
        origen="POST /api/v1/empleados",
        mensaje=f"Empleado creado: '{nuevo_empleado.nombre_completo}' (id={nuevo_empleado.id}) por empleado_id={info['empleado_id']}",
        data={"email": nuevo_empleado.email, "rol_id": nuevo_empleado.rol_id}
    )
    return nuevo_empleado


@router.patch("/{empleado_id}", response_model=EmpleadoAdminResponse)
def actualizar_empleado(
    empleado_id: int,
    payload: EmpleadoUpdate,
    db: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):

    info = verificar_rol_empleado(token_obj.credentials, ["ADMIN", "GERENTE"], db)

    empleado = db.get(Empleado, empleado_id)
    if not empleado:
        raise HTTPException(status_code=404, detail="Empleado no encontrado.")

    datos = payload.model_dump(exclude_unset=True)

    if "email" in datos:
        existente = db.exec(select(Empleado).where(Empleado.email == datos["email"], col(Empleado.id) != empleado_id)).first()
        if existente:
            raise HTTPException(status_code=400, detail="El email ya está en uso por otro empleado.")

    if "documento_identidad" in datos:
        existente = db.exec(select(Empleado).where(Empleado.documento_identidad == datos["documento_identidad"], col(Empleado.id) != empleado_id)).first()
        if existente:
            raise HTTPException(status_code=400, detail="El documento de identidad ya está registrado por otro empleado.")

    if "rol_id" in datos:
        rol = db.get(Rol, datos["rol_id"])
        if not rol:
            raise HTTPException(status_code=404, detail=f"El rol con id={datos['rol_id']} no existe.")

    if "sucursal_id" in datos:
        sucursal = db.get(Sucursal, datos["sucursal_id"])
        if not sucursal or not sucursal.activo:
            raise HTTPException(status_code=404, detail=f"La sucursal con id={datos['sucursal_id']} no existe o está inactiva.")

    for campo, valor in datos.items():
        setattr(empleado, campo, valor)

    db.add(empleado)
    db.commit()
    db.refresh(empleado)

    log_auditoria(
        nivel="INFO",
        origen=f"PATCH /api/v1/empleados/{empleado_id}",
        mensaje=f"Empleado actualizado: id={empleado_id} por empleado_id={info['empleado_id']}",
        data=datos
    )
    return empleado


@router.delete("/{empleado_id}/desactivar", response_model=EmpleadoDesactivarResponse)
def desactivar_empleado(
    empleado_id: int,
    db: Session = Depends(get_session),
    token_obj: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
):

    info = verificar_rol_empleado(token_obj.credentials, ["ADMIN", "GERENTE"], db)

    # Restricción: no puede autodesactivarse
    if info["empleado_id"] == empleado_id:
        raise HTTPException(
            status_code=400,
            detail="No puede desactivar su propia cuenta mientras tiene sesión activa."
        )

    empleado = db.get(Empleado, empleado_id)
    if not empleado:
        raise HTTPException(status_code=404, detail="Empleado no encontrado.")
    if not empleado.activo:
        raise HTTPException(status_code=400, detail="El empleado ya está inactivo.")

    empleado.activo = False
    db.add(empleado)
    db.commit()

    log_auditoria(
        nivel="WARNING",
        origen=f"DELETE /api/v1/empleados/{empleado_id}/desactivar",
        mensaje=f"Empleado desactivado: id={empleado_id}, '{empleado.nombre_completo}' por empleado_id={info['empleado_id']}",
    )

    return EmpleadoDesactivarResponse(
        mensaje=f"Empleado '{empleado.nombre_completo}' desactivado. El acceso ha sido revocado inmediatamente.",
        empleado_id=empleado_id,
        activo=False
    )