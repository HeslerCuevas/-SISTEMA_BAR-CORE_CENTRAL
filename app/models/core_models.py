from typing import Optional, List
from decimal import Decimal
from datetime import datetime, time
import uuid
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, DateTime, text, Numeric, Time
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER

class Sucursal(SQLModel, table=True):
    __tablename__ = "Sucursales"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    nombre: str = Field(sa_column=Column("Nombre", String(100), nullable=False))
    direccion: Optional[str] = Field(default=None, sa_column=Column("Direccion", String(255)))
    activo: bool = Field(sa_column=Column("Activo", Boolean, server_default=text("1")))


class Rol(SQLModel, table=True):
    __tablename__ = "Roles"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    nombre: str = Field(sa_column=Column("Nombre", String(50), unique=True, nullable=False))


class Empleado(SQLModel, table=True):
    __tablename__ = "Empleados"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    rol_id: int = Field(sa_column=Column("RolId", Integer, ForeignKey("Roles.Id"), nullable=False))
    sucursal_id: int = Field(sa_column=Column("SucursalId", Integer, ForeignKey("Sucursales.Id"), nullable=False))
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


class Impuesto(SQLModel, table=True):
    __tablename__ = "Impuestos"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    nombre: str = Field(sa_column=Column("Nombre", String(50), unique=True, nullable=False))
    tasa_porcentaje: Decimal = Field(sa_column=Column("TasaPorcentaje", Numeric(5, 2), nullable=False))
    activo: bool = Field(sa_column=Column("Activo", Boolean, server_default=text("1")))
    ultima_modificacion: datetime = Field(
        sa_column=Column("Ultima_Modificacion", DateTime, server_default=text("GETDATE()"), nullable=False)
    )
    productos: List["Producto"] = Relationship(back_populates="impuesto")


class Categoria(SQLModel, table=True):
    __tablename__ = "Categorias"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    nombre: str = Field(sa_column=Column("Nombre", String(100), unique=True, nullable=False))
    descripcion: Optional[str] = Field(default=None, sa_column=Column("Descripcion", String(255)))
    activo: bool = Field(sa_column=Column("Activo", Boolean, server_default=text("1")))
    ultima_modificacion: datetime = Field(
        sa_column=Column("Ultima_Modificacion", DateTime, server_default=text("GETDATE()"), nullable=False)
    )
    productos: List["Producto"] = Relationship(back_populates="categoria")


class Producto(SQLModel, table=True):
    __tablename__ = "Productos"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    categoria_id: int = Field(sa_column=Column("CategoriaId", Integer, ForeignKey("Categorias.Id"), nullable=False))
    impuesto_id: int = Field(sa_column=Column("ImpuestoId", Integer, ForeignKey("Impuestos.Id"), nullable=False))
    sku: str = Field(sa_column=Column("SKU", String(50), unique=True, nullable=False))
    nombre: str = Field(sa_column=Column("Nombre", String(150), nullable=False))
    descripcion: Optional[str] = Field(default=None, sa_column=Column("Descripcion", String(1000)))
    precio_base: Decimal = Field(sa_column=Column("PrecioBase", Numeric(12, 2), nullable=False))
    costo_promedio: Decimal = Field(default=0.0, sa_column=Column("CostoPromedio", Numeric(12, 2)))
    es_inventariable: bool = Field(default=True, sa_column=Column("EsInventariable", Boolean, server_default=text("1")))
    activo: bool = Field(sa_column=Column("Activo", Boolean, server_default=text("1")))
    ultima_modificacion: datetime = Field(
        sa_column=Column("Ultima_Modificacion", DateTime, server_default=text("GETDATE()")))
    imagen_url: Optional[str] = Field(
        default=None,
        sa_column=Column("ImagenURL", String(1000), nullable=True)
    )
    impuesto: "Impuesto" = Relationship(back_populates="productos")
    categoria: "Categoria" = Relationship(back_populates="productos")

class InventarioActual(SQLModel, table=True):
    __tablename__ = "Inventario_Actual"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    producto_id: int = Field(
        sa_column=Column("ProductoId", Integer, ForeignKey("Productos.Id"), unique=True, nullable=False))
    cantidad_disponible: int = Field(default=0, sa_column=Column("CantidadDisponible", Integer, nullable=False,
                                                                 server_default=text("0")))
    stock_minimo: int = Field(default=5,
                              sa_column=Column("StockMinimo", Integer, nullable=False, server_default=text("5")))
    ultima_actualizacion: datetime = Field(
        sa_column=Column("UltimaActualizacion", DateTime, server_default=text("GETDATE()")))
    ultima_modificacion: datetime = Field(
        sa_column=Column("Ultima_Modificacion", DateTime, server_default=text("GETDATE()")))


class MovimientoInventario(SQLModel, table=True):
    __tablename__ = "Movimientos_Inventario"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    producto_id: int = Field(sa_column=Column("ProductoId", Integer, ForeignKey("Productos.Id"), nullable=False))
    empleado_id: Optional[int] = Field(default=None,
                                       sa_column=Column("EmpleadoId", Integer, ForeignKey("Empleados.Id")))
    tipo_movimiento: str = Field(sa_column=Column("TipoMovimiento", String(20), nullable=False))
    cantidad: int = Field(sa_column=Column("Cantidad", Integer, nullable=False))
    motivo: str = Field(sa_column=Column("Motivo", String(255), nullable=False))
    fecha_movimiento: datetime = Field(sa_column=Column("FechaMovimiento", DateTime, server_default=text("GETDATE()")))
    movimiento_local_uuid: Optional[str] = Field(default=None, nullable=True)
    factura_local_uuid: Optional[uuid.UUID] = Field(default=None,
                                                    sa_column=Column("Factura_Local_UUID", UNIQUEIDENTIFIER))


class PedidoGlobal(SQLModel, table=True):
    __tablename__ = "Pedidos_Global"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    cliente_id: Optional[int] = Field(default=None, sa_column=Column("ClienteId", Integer, ForeignKey("Clientes.Id")))
    empleado_id: Optional[int] = Field(default=None,
                                       sa_column=Column("EmpleadoId", Integer, ForeignKey("Empleados.Id")))
    mesa: Optional[int] = Field(default=None, sa_column=Column("Mesa", String(50)))
    canal_origen: str = Field(sa_column=Column("CanalOrigen", String(50), nullable=False))
    estado: str = Field(default="PENDIENTE",
                        sa_column=Column("Estado", String(50), nullable=False, server_default=text("'PENDIENTE'")))
    subtotal: Decimal = Field(default=0.0,
                              sa_column=Column("Subtotal", Numeric(12, 2), nullable=False, server_default=text("0")))
    total_impuestos: Decimal = Field(default=0.0, sa_column=Column("TotalImpuestos", Numeric(12, 2), nullable=False,
                                                                   server_default=text("0")))
    propina_legal: Optional[Decimal] = Field(default=0.0,
                                             sa_column=Column("PropinaLegal", Numeric(12, 2), server_default=text("0")))
    total_general: Decimal = Field(default=0.0, sa_column=Column("TotalGeneral", Numeric(12, 2), nullable=False,
                                                                 server_default=text("0")))
    fecha_creacion: datetime = Field(sa_column=Column("FechaCreacion", DateTime, server_default=text("GETDATE()")))
    factura_local_uuid: Optional[uuid.UUID] = Field(default=None,
                                                    sa_column=Column("Factura_Local_UUID", UNIQUEIDENTIFIER,
                                                                     index=True))
    propina_extra: Decimal = Field(default=0.0,
                                   sa_column=Column("PropinaExtra", Numeric(12, 2), nullable=False,
                                                    server_default=text("0")))


class DetallePedido(SQLModel, table=True):
    __tablename__ = "Detalles_Pedido"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    pedido_id: int = Field(sa_column=Column("PedidoId", Integer, ForeignKey("Pedidos_Global.Id"), nullable=False))
    producto_id: int = Field(sa_column=Column("ProductoId", Integer, ForeignKey("Productos.Id"), nullable=False))
    cantidad: int = Field(sa_column=Column("Cantidad", Integer, nullable=False))
    precio_unitario_historico: Decimal = Field(
        sa_column=Column("PrecioUnitarioHistorico", Numeric(12, 2), nullable=False))
    impuesto_historico: Decimal = Field(sa_column=Column("ImpuestoHistorico", Numeric(5, 2), nullable=False))
    monto_impuesto: Decimal = Field(default=0.0, sa_column=Column("MontoImpuesto", Numeric(12, 2), nullable=False,
                                                                  server_default=text("0")))
    subtotal_linea: Decimal = Field(default=0.0, sa_column=Column("SubtotalLinea", Numeric(12, 2), nullable=False,
                                                                  server_default=text("0")))
    detalle_local_uuid: Optional[uuid.UUID] = Field(default=None,
                                                    sa_column=Column("Detalle_Local_UUID", UNIQUEIDENTIFIER))


class CoreLog(SQLModel, table=True):
    __tablename__ = "Core_Logs"
    log_id: Optional[int] = Field(default=None, sa_column=Column("Log_Id", Integer, primary_key=True))
    fecha_hora: datetime = Field(sa_column=Column("Fecha_Hora", DateTime, server_default=text("GETDATE()")))
    nivel: str = Field(sa_column=Column("Nivel", String(20), nullable=False))
    origen: str = Field(sa_column=Column("Origen", String(100), nullable=False))
    mensaje: str = Field(sa_column=Column("Mensaje", String, nullable=False))
    data_json: Optional[str] = Field(default=None, sa_column=Column("Data_JSON", String))


# ─────────────────────────────────────────────────────────────────
# NUEVOS MODELOS
# ─────────────────────────────────────────────────────────────────

class Mesa(SQLModel, table=True):
    __tablename__ = "Mesas"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    numero: int = Field(sa_column=Column("Numero", Integer, unique=True, nullable=False))
    descripcion: Optional[str] = Field(default=None, sa_column=Column("Descripcion", String(255)))
    capacidad: int = Field(default=4, sa_column=Column("Capacidad", Integer, nullable=False, server_default=text("4")))
    activo: bool = Field(default=True, sa_column=Column("Activo", Boolean, server_default=text("1")))
    qr_token: Optional[str] = Field(default=None, sa_column=Column("QrToken", String(100)))
    fecha_creacion: datetime = Field(sa_column=Column("FechaCreacion", DateTime, server_default=text("GETDATE()")))


class Promocion(SQLModel, table=True):
    __tablename__ = "Promociones"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    nombre: str = Field(sa_column=Column("Nombre", String(150), unique=True, nullable=False))
    descripcion: Optional[str] = Field(default=None, sa_column=Column("Descripcion", String(500)))
    # PORCENTAJE | MONTO_FIJO
    tipo_descuento: str = Field(sa_column=Column("TipoDescuento", String(20), nullable=False))
    valor: Decimal = Field(sa_column=Column("Valor", Numeric(12, 2), nullable=False))
    fecha_inicio: datetime = Field(sa_column=Column("FechaInicio", DateTime, nullable=False))
    fecha_fin: Optional[datetime] = Field(default=None, sa_column=Column("FechaFin", DateTime))
    activo: bool = Field(default=True, sa_column=Column("Activo", Boolean, server_default=text("1")))
    prioridad: int = Field(default=0, sa_column=Column("Prioridad", Integer, nullable=False, server_default=text("0")))
    # TODOS | PRODUCTOS | CATEGORIAS
    aplica_a: str = Field(default="TODOS", sa_column=Column("AplicaA", String(20), nullable=False, server_default=text("'TODOS'")))
    aplica_happy_hour: bool = Field(default=False, sa_column=Column("AplicaHappyHour", Boolean, server_default=text("0")))
    hora_inicio_hh: Optional[str] = Field(default=None, sa_column=Column("HoraInicioHH", String(5)))
    hora_fin_hh: Optional[str] = Field(default=None, sa_column=Column("HoraFinHH", String(5)))
    fecha_creacion: datetime = Field(sa_column=Column("FechaCreacion", DateTime, server_default=text("GETDATE()")))


class PromocionProducto(SQLModel, table=True):
    __tablename__ = "Promociones_Productos"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    promocion_id: int = Field(sa_column=Column("PromocionId", Integer, ForeignKey("Promociones.Id"), nullable=False))
    producto_id: int = Field(sa_column=Column("ProductoId", Integer, ForeignKey("Productos.Id"), nullable=False))


class PromocionCategoria(SQLModel, table=True):
    __tablename__ = "Promociones_Categorias"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    promocion_id: int = Field(sa_column=Column("PromocionId", Integer, ForeignKey("Promociones.Id"), nullable=False))
    categoria_id: int = Field(sa_column=Column("CategoriaId", Integer, ForeignKey("Categorias.Id"), nullable=False))


class SecuenciaNcf(SQLModel, table=True):
    __tablename__ = "Secuencias_NCF"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    tipo_ncf: str = Field(sa_column=Column("TipoNcf", String(10), nullable=False))
    serie: str = Field(sa_column=Column("Serie", String(10), nullable=False))
    rango_desde: int = Field(sa_column=Column("RangoDesde", Integer, nullable=False))
    rango_hasta: int = Field(sa_column=Column("RangoHasta", Integer, nullable=False))
    secuencia_actual: int = Field(sa_column=Column("SecuenciaActual", Integer, nullable=False))
    fecha_vencimiento: datetime = Field(sa_column=Column("FechaVencimiento", DateTime, nullable=False))
    activo: bool = Field(default=True, sa_column=Column("Activo", Boolean, server_default=text("1")))
    sucursal_id: Optional[int] = Field(default=None, sa_column=Column("SucursalId", Integer, ForeignKey("Sucursales.Id")))
    fecha_creacion: datetime = Field(sa_column=Column("FechaCreacion", DateTime, server_default=text("GETDATE()")))


class HistorialNcf(SQLModel, table=True):
    __tablename__ = "Historial_NCF"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    secuencia_id: int = Field(sa_column=Column("SecuenciaId", Integer, ForeignKey("Secuencias_NCF.Id"), nullable=False))
    ncf_asignado: str = Field(sa_column=Column("NcfAsignado", String(20), nullable=False))
    pedido_id: Optional[int] = Field(default=None, sa_column=Column("PedidoId", Integer, ForeignKey("Pedidos_Global.Id")))
    empleado_id: Optional[int] = Field(default=None, sa_column=Column("EmpleadoId", Integer, ForeignKey("Empleados.Id")))
    fecha_asignacion: datetime = Field(sa_column=Column("FechaAsignacion", DateTime, server_default=text("GETDATE()")))


class PasswordResetToken(SQLModel, table=True):
    __tablename__ = "Password_Reset_Tokens"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    token_hash: str = Field(sa_column=Column("TokenHash", String(255), nullable=False, index=True))
    # EMPLEADO | CLIENTE
    entidad_tipo: str = Field(sa_column=Column("EntidadTipo", String(20), nullable=False))
    entidad_id: int = Field(sa_column=Column("EntidadId", Integer, nullable=False))
    expira_en: datetime = Field(sa_column=Column("ExpiraEn", DateTime, nullable=False))
    usado: bool = Field(default=False, sa_column=Column("Usado", Boolean, server_default=text("0")))
    fecha_creacion: datetime = Field(sa_column=Column("FechaCreacion", DateTime, server_default=text("GETDATE()")))


class ModificadorItem(SQLModel, table=True):
    __tablename__ = "Modificadores_Item"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    detalle_pedido_id: int = Field(
        sa_column=Column("DetallePedidoId", Integer, ForeignKey("Detalles_Pedido.Id"), nullable=False)
    )
    descripcion: str = Field(sa_column=Column("Descripcion", String(255), nullable=False))
    fecha_registro: datetime = Field(sa_column=Column("FechaRegistro", DateTime, server_default=text("GETDATE()")))


class DivisionCuenta(SQLModel, table=True):
    __tablename__ = "Division_Cuenta"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    pedido_id: int = Field(sa_column=Column("PedidoId", Integer, ForeignKey("Pedidos_Global.Id"), nullable=False))
    numero_partes: int = Field(sa_column=Column("NumeroPartes", Integer, nullable=False))
    monto_por_parte: Decimal = Field(sa_column=Column("MontoPorParte", Numeric(12, 2), nullable=False))
    # JSON string con montos personalizados por parte: [{"parte":1,"monto":500},...]
    montos_personalizados_json: Optional[str] = Field(
        default=None, sa_column=Column("MontosPersonalizadosJson", String(2000))
    )
    empleado_id: Optional[int] = Field(default=None, sa_column=Column("EmpleadoId", Integer, ForeignKey("Empleados.Id")))
    fecha_division: datetime = Field(sa_column=Column("FechaDivision", DateTime, server_default=text("GETDATE()")))