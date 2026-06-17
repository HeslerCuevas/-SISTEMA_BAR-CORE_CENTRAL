"""
Crea todas las tablas definidas en los modelos SQLModel dentro de la base de datos
apuntada por DATABASE_URL. Correrlo una sola vez, despues de que el contenedor de
SQL Server este arriba y la base de datos Core_Master_DB ya exista.

Uso:
    python create_tables.py
"""
import os
from dotenv import load_dotenv
from sqlmodel import SQLModel, create_engine

from pathlib import Path

# IMPORTANTE: ajusta esta linea para que apunte al archivo/modulo real donde
# guardaste las clases (Sucursal, Rol, Empleado, Cliente, Impuesto, Categoria,
# Producto, InventarioActual, MovimientoInventario, PedidoGlobal, DetallePedido, CoreLog).
# Si todo esta en un archivo llamado models.py en la misma carpeta, deja la linea como esta.
from models import (  # noqa: F401
    Sucursal,
    Rol,
    Empleado,
    Cliente,
    Impuesto,
    Categoria,
    Producto,
    InventarioActual,
    MovimientoInventario,
    PedidoGlobal,
    DetallePedido,
    CoreLog,
)

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

DATABASE_URL_DOCKER = os.environ["DATABASE_URL_DOCKER"]

# echo=True imprime el SQL generado, util para ver exactamente que se esta creando
engine = create_engine(DATABASE_URL_DOCKER, echo=True)

if __name__ == "__main__":
    SQLModel.metadata.create_all(engine)
    print("Tablas creadas correctamente en Core_Master_DB.")




# CONECTAR A LA TETMINAL DB VIA EL CONTENEDOR
# [1]
# docker exec -it sqlserver_core bash

#[2]
# /opt/mssql-tools18/bin/sqlcmd \
# -S localhost \
# -U sa \
# -P 'Qa123456@' \
# -C
