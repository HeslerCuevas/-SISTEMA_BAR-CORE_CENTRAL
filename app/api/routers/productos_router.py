from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, col
from typing import List
from app.db.database import get_session

from app.models.core_models import Producto, InventarioActual, Impuesto, Categoria
from app.schemas.producto_schema import ProductoCreate, ProductoResponse, CategoriaResponse, ImpuestoResponse

router = APIRouter(
    prefix="/api/v1/productos",
    tags=["Módulo de Productos"]
)


@router.get("/", response_model=List[ProductoResponse])
def listar_productos(session: Session = Depends(get_session)):
    statement = (
        select(
            Producto,
            col(Impuesto.tasa_porcentaje).label("tasa_impuesto"),
            col(InventarioActual.cantidad_disponible).label("cantidad_disponible")
        )
        .join(Impuesto, col(Producto.impuesto_id) == col(Impuesto.id))
        .outerjoin(InventarioActual, col(Producto.id) == col(InventarioActual.producto_id))
    )

    results = session.exec(statement).all()

    lista_final = []
    for producto, tasa, stock in results:
        p_data = producto.model_dump()
        p_data["tasa_impuesto"] = (tasa / 100) if tasa is not None else 0

        if not producto.es_inventariable:
            p_data["cantidad_disponible"] = 9999
        else:
            p_data["cantidad_disponible"] = stock if stock is not None else 0

        p_data["categoria_id"] = producto.categoria_id
        lista_final.append(p_data)
    return lista_final


@router.get("/por-categoria/{categoria_id}", response_model=List[ProductoResponse])
def listar_productos_por_categoria(categoria_id: int, session: Session = Depends(get_session)):
    statement = (
        select(
            Producto,
            col(Impuesto.tasa_porcentaje).label("tasa_impuesto"),
            col(InventarioActual.cantidad_disponible).label("cantidad_disponible")
        )
        .join(Impuesto, col(Producto.impuesto_id) == col(Impuesto.id))
        .outerjoin(InventarioActual, col(Producto.id) == col(InventarioActual.producto_id))
        .where(col(Producto.categoria_id) == categoria_id)
        .where(col(Producto.activo) == True)
    )

    results = session.exec(statement).all()

    lista_final = []
    for producto, tasa, stock in results:
        p_data = producto.model_dump()
        p_data["imagen_url"] = producto.imagen_url
        p_data["tasa_impuesto"] = (tasa / 100) if tasa is not None else 0

        if not producto.es_inventariable:
            p_data["cantidad_disponible"] = 9999
        else:
            p_data["cantidad_disponible"] = stock if stock is not None else 0

        p_data["categoria_id"] = producto.categoria_id
        lista_final.append(p_data)
    return lista_final


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

        return obtener_producto(nuevo_producto.id, session)

    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")


@router.get("/categorias", response_model=List[CategoriaResponse])
def listar_categorias(session: Session = Depends(get_session)):
    statement = select(Categoria).where(col(Categoria.activo) == True)
    categorias = session.exec(statement).all()

    return categorias


@router.get("/impuestos", response_model=List[ImpuestoResponse])
def listar_impuestos(session: Session = Depends(get_session)):
    statement = select(Impuesto)
    impuestos = session.exec(statement).all()

    resultados = []
    for imp in impuestos:
        resultados.append({
            "id": imp.id,
            "nombre": imp.nombre,
            "tasa_porcentaje": float(imp.tasa_porcentaje)
        })

    return resultados

@router.get("/{producto_id}", response_model=ProductoResponse)
def obtener_producto(producto_id: int, session: Session = Depends(get_session)):
    statement = (
        select(
            Producto,
            col(Impuesto.tasa_porcentaje).label("tasa"),
            col(InventarioActual.cantidad_disponible).label("stock")
        )
        .join(Impuesto, col(Producto.impuesto_id) == col(Impuesto.id))
        .outerjoin(InventarioActual, col(Producto.id) == col(InventarioActual.producto_id))
        .where(col(Producto.id) == producto_id)
    )
    result = session.exec(statement).first()

    if not result:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    producto, tasa, stock = result
    p_data = producto.model_dump()
    p_data["tasa_impuesto"] = (tasa / 100) if tasa is not None else 0

    if not producto.es_inventariable:
        p_data["cantidad_disponible"] = 9999
    else:
        p_data["cantidad_disponible"] = stock if stock is not None else 0

    return p_data

