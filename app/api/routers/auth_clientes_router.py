from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from datetime import datetime

from app.db.database import get_session
from app.models.core_models import Cliente
from core.security import verify_password, get_password_hash, create_access_token

from app.schemas.auth_schema import (
    ClienteRegistroRequest,
    ClienteRegistroResponse,
    ClienteLoginRequest,
    ClienteLoginResponse
)

router = APIRouter(prefix="/api/v1/clientes/auth", tags=["Seguridad - Clientes Móvil"])


@router.post("/registro", response_model=ClienteRegistroResponse, status_code=201)
def registrar_cliente(
        request: ClienteRegistroRequest,
        session: Session = Depends(get_session)
):
    statement = select(Cliente).where(Cliente.email == request.email)
    cliente_existente = session.exec(statement).first()

    if cliente_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este correo electrónico ya está registrado."
        )

    hashed_password = get_password_hash(request.password_plano)

    nuevo_cliente = Cliente(
        nombre_completo=request.nombre_completo,
        email=request.email,
        telefono=request.telefono,
        password_hash=hashed_password,
        fecha_registro=datetime.utcnow(),
        activo=True
    )

    session.add(nuevo_cliente)
    session.commit()
    session.refresh(nuevo_cliente)

    return ClienteRegistroResponse(
        mensaje="Cuenta de cliente creada exitosamente.",
        cliente_id=nuevo_cliente.id,
        email=nuevo_cliente.email
    )


@router.post("/login", response_model=ClienteLoginResponse)
def login_cliente(
        request: ClienteLoginRequest,
        session: Session = Depends(get_session)
):
    statement = select(Cliente).where(Cliente.email == request.email)
    cliente = session.exec(statement).first()

    if not cliente or not verify_password(request.password_plano, cliente.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos"
        )

    if not cliente.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta cuenta ha sido desactivada."
        )

    token_data = {
        "sub": str(cliente.id),
        "canal": "MOVIL",
        "nombre": cliente.nombre_completo,
        "email": cliente.email
    }

    access_token = create_access_token(data=token_data)

    return ClienteLoginResponse(
        access_token=access_token,
        token_type="bearer",
        canal="MOVIL",
        cliente_id=cliente.id,
        nombre_completo=cliente.nombre_completo
    )