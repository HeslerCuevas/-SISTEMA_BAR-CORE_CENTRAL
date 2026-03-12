from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, DateTime, text, Numeric


class Rol(SQLModel, table=True):
    __tablename__ = "Roles"
    # Forzamos que en SQL se use "Id" y "Nombre"
    id: Optional[int] = Field(sa_column=Column("Id", Integer, primary_key=True))
    nombre: str = Field(sa_column=Column("Nombre", String(50), unique=True, nullable=False))


class Empleado(SQLModel, table=True):
    __tablename__ = "Empleados"
    id: Optional[int] = Field(sa_column=Column("Id", Integer, primary_key=True))

    # Aquí está el truco: sa_column define el nombre real en SQL Server
    rol_id: int = Field(sa_column=Column("RolId", Integer, ForeignKey("Roles.Id"), nullable=False))
    documento_identidad: str = Field(sa_column=Column("DocumentoIdentidad", String(20), unique=True, nullable=False))
    nombre_completo: str = Field(sa_column=Column("NombreCompleto", String(150), nullable=False))
    email: str = Field(sa_column=Column("Email", String(150), unique=True, nullable=False))
    password_hash: str = Field(sa_column=Column("PasswordHash", String(255), nullable=False))
    activo: bool = Field(sa_column=Column("Activo", Boolean, server_default=text("1")))

class Cliente(SQLModel, table=True):
    __tablename__ = "Clientes"
    id: Optional[int] = Field(default=None, primary_key=True, alias="Id")
    nombre_completo: str = Field(sa_type=String(150), alias="NombreCompleto")
    email: str = Field(unique=True, sa_type=String(150), alias="Email")
    telefono: Optional[str] = Field(default=None, sa_type=String(20), alias="Telefono") # <--- Recuperado
    password_hash: str = Field(sa_type=String(255), alias="PasswordHash")
    fecha_registro: datetime = Field(
        sa_column=Column(DateTime, server_default=text("GETDATE()")),
        alias="FechaRegistro"
    )
    activo: bool = Field(default=True, alias="Activo")


class CoreLog(SQLModel, table=True):
    __tablename__ = "Core_Logs"
    log_id: Optional[int] = Field(default=None, primary_key=True, alias="Log_Id")
    fecha_hora: datetime = Field(
        sa_column=Column(DateTime, server_default=text("GETDATE()")),
        alias="Fecha_Hora"
    )
    nivel: str = Field(sa_type=String(20), alias="Nivel") # INFO, ERROR, etc.
    origen: str = Field(sa_type=String(100), alias="Origen")
    mensaje: str = Field(alias="Mensaje")
    data_json: Optional[str] = Field(default=None, alias="Data_JSON")

class Impuesto(SQLModel, table=True):
    __tablename__ = "Impuestos"
    id: Optional[int] = Field(default=None, primary_key=True, alias="Id")
    nombre: str = Field(unique=True, sa_type=String(50), alias="Nombre")
    # Cambio de float a Numeric para precisión total
    tasa_porcentaje: float = Field(sa_column=Column(Numeric(5, 2)), alias="TasaPorcentaje")
    activo: bool = Field(default=True, alias="Activo")

class Producto(SQLModel, table=True):
    __tablename__ = "Productos"
    id: Optional[int] = Field(default=None, primary_key=True, alias="Id")
    categoria_id: int = Field(foreign_key="Categorias.Id", alias="CategoriaId")
    impuesto_id: int = Field(foreign_key="Impuestos.Id", alias="ImpuestoId")
    sku: str = Field(unique=True, sa_type=String(50), alias="SKU")
    nombre: str = Field(sa_type=String(150), alias="Nombre")
    descripcion: Optional[str] = Field(default=None, alias="Descripcion")
    # Cambio de float a Numeric para que el precio base sea exacto
    precio_base: float = Field(sa_column=Column(Numeric(12, 2)), alias="PrecioBase")
    es_servicio: bool = Field(default=False) # Extra para requerimiento INTEC
    activo: bool = Field(default=True, alias="Activo")

class Categoria(SQLModel, table=True):
    __tablename__ = "Categorias"
    id: Optional[int] = Field(default=None, primary_key=True, alias="Id")
    nombre: str = Field(unique=True, sa_type=String(100), alias="Nombre")
    descripcion: Optional[str] = Field(default=None, sa_type=String(255), alias="Descripcion")
    activo: bool = Field(default=True, alias="Activo")


class InventarioActual(SQLModel, table=True):
    __tablename__ = "Inventario_Actual"

    id: Optional[int] = Field(default=None, primary_key=True, alias="Id")
    # Relación 1:1 con Productos. Cada producto tiene una sola fila de stock.
    producto_id: int = Field(unique=True, foreign_key="Productos.Id", alias="ProductoId")
    cantidad_disponible: int = Field(default=0, alias="CantidadDisponible")
    stock_minimo: int = Field(default=5, alias="StockMinimo")
    ultima_actualizacion: datetime = Field(
        sa_column=Column(DateTime, server_default=text("GETDATE()")),
        alias="UltimaActualizacion"
    )


class MovimientoInventario(SQLModel, table=True):
    __tablename__ = "Movimientos_Inventario"

    id: Optional[int] = Field(default=None, primary_key=True, alias="Id")
    producto_id: int = Field(foreign_key="Productos.Id", alias="ProductoId")
    # El empleado que realizó el ajuste o entrada (ej. el Bartender que recibió el camión)
    empleado_id: Optional[int] = Field(default=None, foreign_key="Empleados.Id", alias="EmpleadoId")

    # Valores permitidos según tu script: 'ENTRADA', 'SALIDA', 'AJUSTE'
    tipo_movimiento: str = Field(sa_type=String(20), alias="TipoMovimiento")
    cantidad: int = Field(alias="Cantidad")
    motivo: str = Field(sa_type=String(255), alias="Motivo")
    fecha_movimiento: datetime = Field(
        sa_column=Column(DateTime, server_default=text("GETDATE()")),
        alias="FechaMovimiento"
    )


class PedidoGlobal(SQLModel, table=True):
    __tablename__ = "Pedidos_Global"

    id: Optional[int] = Field(default=None, primary_key=True, alias="Id")
    cliente_id: Optional[int] = Field(default=None, foreign_key="Clientes.Id", alias="ClienteId")
    empleado_id: Optional[int] = Field(default=None, foreign_key="Empleados.Id", alias="EmpleadoId")
    canal_origen: str = Field(sa_type=String(50), alias="CanalOrigen")
    estado: str = Field(default="PENDIENTE", sa_type=String(50), alias="Estado")

    subtotal: float = Field(sa_column=Column(Numeric(12, 2)), alias="Subtotal")
    total_impuestos: float = Field(sa_column=Column(Numeric(12, 2)), alias="TotalImpuestos")
    total_general: float = Field(sa_column=Column(Numeric(12, 2)), alias="TotalGeneral")

    fecha_creacion: datetime = Field(
        sa_column=Column(DateTime, server_default=text("GETDATE()")),
        alias="FechaCreacion"
    )


class DetallePedido(SQLModel, table=True):
    __tablename__ = "Detalles_Pedido"

    id: Optional[int] = Field(default=None, primary_key=True, alias="Id")
    pedido_id: int = Field(foreign_key="Pedidos_Global.Id", alias="PedidoId")
    producto_id: int = Field(foreign_key="Productos.Id", alias="ProductoId")
    cantidad: int = Field(alias="Cantidad")

    precio_unitario_historico: float = Field(sa_column=Column(Numeric(12, 2)), alias="PrecioUnitarioHistorico")
    impuesto_historico: float = Field(sa_column=Column(Numeric(5, 2)), alias="ImpuestoHistorico")
    monto_impuesto: float = Field(sa_column=Column(Numeric(12, 2)), alias="MontoImpuesto")
    subtotal_linea: float = Field(sa_column=Column(Numeric(12, 2)), alias="SubtotalLinea")