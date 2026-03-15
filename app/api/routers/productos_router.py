from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List

from app.db.database import get_session
from app.models.core_models import Producto, InventarioActual
from app.schemas.producto_schema import ProductoCreate, ProductoResponse

router = APIRouter(
    prefix="/api/v1/productos",
    tags=["Módulo de Productos"]
)


@router.post("/", response_model=ProductoResponse, status_code=201)
def crear_producto(producto_in: ProductoCreate, session: Session = Depends(get_session)):
    try:
        nuevo_producto = Producto(**producto_in.model_dump())
        session.add(nuevo_producto)

        session.flush()

        if nuevo_producto.es_inventariable:
            nuevo_inventario = InventarioActual(
                producto_id=nuevo_producto.id,
                cantidad_disponible=0,
                stock_minimo=5
            )
            session.add(nuevo_inventario)

        session.commit()
        session.refresh(nuevo_producto)

        return nuevo_producto

    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=f"Error al crear producto e inventario: {str(e)}")

@router.get("/", response_model=List[ProductoResponse])
def listar_productos(session: Session = Depends(get_session)):
    productos = session.exec(select(Producto)).all()
    return productos


@router.get("/{producto_id}", response_model=ProductoResponse)
def obtener_producto(producto_id: int, session: Session = Depends(get_session)):
    producto = session.get(Producto, producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto


@router.put("/{producto_id}", response_model=ProductoResponse)
def actualizar_producto(producto_id: int, producto_in: ProductoCreate, session: Session = Depends(get_session)):
    producto_db = session.get(Producto, producto_id)
    if not producto_db:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    producto_data = producto_in.dict(exclude_unset=True)
    for key, value in producto_data.items():
        setattr(producto_db, key, value)

    session.add(producto_db)
    session.commit()
    session.refresh(producto_db)
    return producto_db