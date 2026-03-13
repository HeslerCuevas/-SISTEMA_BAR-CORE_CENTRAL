from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, DateTime, text, Numeric

# ==========================================
# 1. SEGURIDAD Y ACCESOS
# ==========================================

class Rol(SQLModel, table=True):
    __tablename__ = "Roles"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    nombre: str = Field(sa_column=Column("Nombre", String(50), unique=True, nullable=False))

class Empleado(SQLModel, table=True):
    __tablename__ = "Empleados"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    rol_id: int = Field(sa_column=Column("RolId", Integer, ForeignKey("Roles.Id"), nullable=False))
    documento_identidad: str = Field(sa_column=Column("DocumentoIdentidad", String(20), unique=True, nullable=False))
    nombre_completo: str = Field(sa_column=Column("NombreCompleto", String(150), nullable=False))
    email: str = Field(sa_column=Column("Email", String(150), unique=True, nullable=False))
    password_hash: str = Field(sa_column=Column("PasswordHash", String(255), nullable=False))
    activo: bool = Field(sa_column=Column("Activo", Boolean, server_default=text("1")))

class Cliente(SQLModel, table=True):
    __tablename__ = "Clientes"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    nombre_completo: str = Field(sa_column=Column("NombreCompleto", String(150), nullable=False))
    email: str = Field(sa_column=Column("Email", String(150), unique=True, nullable=False))
    telefono: Optional[str] = Field(default=None, sa_column=Column("Telefono", String(20)))
    password_hash: str = Field(sa_column=Column("PasswordHash", String(255), nullable=False))
    fecha_registro: datetime = Field(sa_column=Column("FechaRegistro", DateTime, server_default=text("GETDATE()")))
    activo: bool = Field(sa_column=Column("Activo", Boolean, server_default=text("1")))

# ==========================================
# 2. CATÁLOGO Y FINANZAS
# ==========================================

class Impuesto(SQLModel, table=True):
    __tablename__ = "Impuestos"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    nombre: str = Field(sa_column=Column("Nombre", String(50), unique=True, nullable=False))
    tasa_porcentaje: float = Field(sa_column=Column("TasaPorcentaje", Numeric(5, 2), nullable=False))
    activo: bool = Field(sa_column=Column("Activo", Boolean, server_default=text("1")))

class Categoria(SQLModel, table=True):
    __tablename__ = "Categorias"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    nombre: str = Field(sa_column=Column("Nombre", String(100), unique=True, nullable=False))
    descripcion: Optional[str] = Field(default=None, sa_column=Column("Descripcion", String(255)))
    activo: bool = Field(sa_column=Column("Activo", Boolean, server_default=text("1")))


class Producto(SQLModel, table=True):
    __tablename__ = "Productos"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    categoria_id: int = Field(sa_column=Column("CategoriaId", Integer, ForeignKey("Categorias.Id"), nullable=False))
    impuesto_id: int = Field(sa_column=Column("ImpuestoId", Integer, ForeignKey("Impuestos.Id"), nullable=False))
    sku: str = Field(sa_column=Column("SKU", String(50), unique=True, nullable=False))
    nombre: str = Field(sa_column=Column("Nombre", String(150), nullable=False))
    descripcion: Optional[str] = Field(default=None, sa_column=Column("Descripcion", String(1000)))
    precio_base: float = Field(sa_column=Column("PrecioBase", Numeric(12, 2), nullable=False))
    costo_promedio: float = Field(default=0.0, sa_column=Column("CostoPromedio", Numeric(12, 2)))
    es_inventariable: bool = Field(default=True, sa_column=Column("EsInventariable", Boolean, server_default=text("1")))
    activo: bool = Field(sa_column=Column("Activo", Boolean, server_default=text("1")))

# ==========================================
# 3. INVENTARIO Y KARDEX
# ==========================================

class InventarioActual(SQLModel, table=True):
    __tablename__ = "Inventario_Actual"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    producto_id: int = Field(sa_column=Column("ProductoId", Integer, ForeignKey("Productos.Id"), unique=True, nullable=False))
    cantidad_disponible: int = Field(default=0, sa_column=Column("CantidadDisponible", Integer, nullable=False, server_default=text("0")))
    stock_minimo: int = Field(default=5, sa_column=Column("StockMinimo", Integer, nullable=False, server_default=text("5")))
    ultima_actualizacion: datetime = Field(sa_column=Column("UltimaActualizacion", DateTime, server_default=text("GETDATE()")))

class MovimientoInventario(SQLModel, table=True):
    __tablename__ = "Movimientos_Inventario"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    producto_id: int = Field(sa_column=Column("ProductoId", Integer, ForeignKey("Productos.Id"), nullable=False))
    empleado_id: Optional[int] = Field(default=None, sa_column=Column("EmpleadoId", Integer, ForeignKey("Empleados.Id")))
    tipo_movimiento: str = Field(sa_column=Column("TipoMovimiento", String(20), nullable=False))
    cantidad: int = Field(sa_column=Column("Cantidad", Integer, nullable=False))
    motivo: str = Field(sa_column=Column("Motivo", String(255), nullable=False))
    fecha_movimiento: datetime = Field(sa_column=Column("FechaMovimiento", DateTime, server_default=text("GETDATE()")))

# ==========================================
# 4. VENTAS Y PEDIDOS
# ==========================================

class PedidoGlobal(SQLModel, table=True):
    __tablename__ = "Pedidos_Global"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    cliente_id: Optional[int] = Field(default=None, sa_column=Column("ClienteId", Integer, ForeignKey("Clientes.Id")))
    empleado_id: Optional[int] = Field(default=None, sa_column=Column("EmpleadoId", Integer, ForeignKey("Empleados.Id")))
    canal_origen: str = Field(sa_column=Column("CanalOrigen", String(50), nullable=False))
    estado: str = Field(default="PENDIENTE", sa_column=Column("Estado", String(50), nullable=False, server_default=text("'PENDIENTE'")))
    subtotal: float = Field(default=0.0, sa_column=Column("Subtotal", Numeric(12, 2), nullable=False, server_default=text("0")))
    total_impuestos: float = Field(default=0.0, sa_column=Column("TotalImpuestos", Numeric(12, 2), nullable=False, server_default=text("0")))
    total_general: float = Field(default=0.0, sa_column=Column("TotalGeneral", Numeric(12, 2), nullable=False, server_default=text("0")))
    fecha_creacion: datetime = Field(sa_column=Column("FechaCreacion", DateTime, server_default=text("GETDATE()")))

class DetallePedido(SQLModel, table=True):
    __tablename__ = "Detalles_Pedido"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    pedido_id: int = Field(sa_column=Column("PedidoId", Integer, ForeignKey("Pedidos_Global.Id"), nullable=False))
    producto_id: int = Field(sa_column=Column("ProductoId", Integer, ForeignKey("Productos.Id"), nullable=False))
    cantidad: int = Field(sa_column=Column("Cantidad", Integer, nullable=False))
    precio_unitario_historico: float = Field(sa_column=Column("PrecioUnitarioHistorico", Numeric(12, 2), nullable=False))
    impuesto_historico: float = Field(sa_column=Column("ImpuestoHistorico", Numeric(5, 2), nullable=False))
    monto_impuesto: float = Field(default=0.0, sa_column=Column("MontoImpuesto", Numeric(12, 2), nullable=False, server_default=text("0")))
    subtotal_linea: float = Field(default=0.0, sa_column=Column("SubtotalLinea", Numeric(12, 2), nullable=False, server_default=text("0")))

# ==========================================
# 5. TRAZABILIDAD
# ==========================================

class CoreLog(SQLModel, table=True):
    __tablename__ = "Core_Logs"
    log_id: Optional[int] = Field(default=None, sa_column=Column("Log_Id", Integer, primary_key=True))
    fecha_hora: datetime = Field(sa_column=Column("Fecha_Hora", DateTime, server_default=text("GETDATE()")))
    nivel: str = Field(sa_column=Column("Nivel", String(20), nullable=False))
    origen: str = Field(sa_column=Column("Origen", String(100), nullable=False))
    mensaje: str = Field(sa_column=Column("Mensaje", String, nullable=False))
    data_json: Optional[str] = Field(default=None, sa_column=Column("Data_JSON", String))