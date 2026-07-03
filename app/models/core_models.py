from typing import Optional, List
from decimal import Decimal
from datetime import datetime
import uuid
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, Integer, BigInteger, ForeignKey, Boolean, DateTime, text, Numeric
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
    # PRODUCTO = legacy unit-level stock | INGREDIENTES = recipe-based | NINGUNO = no stock tracking
    tipo_control_inventario: str = Field(
        default="PRODUCTO",
        sa_column=Column("TipoControlInventario", String(20), nullable=False, server_default=text("'PRODUCTO'"))
    )
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
    # AUTOMATICA | ELEGIBILIDAD | CODIGO_PROMO | MANUAL
    tipo_aplicacion: str = Field(default="AUTOMATICA", sa_column=Column("TipoAplicacion", String(20), nullable=False, server_default=text("'AUTOMATICA'")))
    aplica_happy_hour: bool = Field(default=False, sa_column=Column("AplicaHappyHour", Boolean, server_default=text("0")))
    hora_inicio_hh: Optional[str] = Field(default=None, sa_column=Column("HoraInicioHH", String(5)))
    hora_fin_hh: Optional[str] = Field(default=None, sa_column=Column("HoraFinHH", String(5)))
    precio_minimo_final: Optional[Decimal] = Field(default=None, sa_column=Column("PrecioMinimoFinal", Numeric(12, 2)))
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

    # Mapeado 1:1 con la columna 'DetallePedidoUuid' de tipo uniqueidentifier que sale en tu consulta
    detalle_pedido_uuid: uuid.UUID = Field(
        sa_column=Column(
            "DetallePedidoUuid",
            UNIQUEIDENTIFIER,
            nullable=False
        )
    )
    descripcion: str = Field(sa_column=Column("Descripcion", String(255), nullable=False))
    fecha_registro: datetime = Field(
        sa_column=Column("FechaRegistro", DateTime, server_default=text("GETDATE()"), nullable=True)
    )
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


# ─────────────────────────────────────────────────────────────────
# SISTEMA DE INVENTARIO POR INGREDIENTES
# ─────────────────────────────────────────────────────────────────

class CategoriaIngrediente(SQLModel, table=True):
    """Master data: ingredient categories (e.g., Spirits, Mixers, Garnishes)."""
    __tablename__ = "Categorias_Ingredientes"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    nombre: str = Field(sa_column=Column("Nombre", String(100), unique=True, nullable=False))
    descripcion: Optional[str] = Field(default=None, sa_column=Column("Descripcion", String(500)))
    activo: bool = Field(default=True, sa_column=Column("Activo", Boolean, nullable=False, server_default=text("1")))
    ultima_modificacion: datetime = Field(
        sa_column=Column("Ultima_Modificacion", DateTime, nullable=False, server_default=text("GETDATE()"))
    )


class Ingrediente(SQLModel, table=True):
    """
    Ingredient master with real-time stock tracking.
    UnidadMedida allowed values: ml | l | g | kg | unidad | pieza | botella | lata
    """
    __tablename__ = "Ingredientes"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    categoria_id: int = Field(
        sa_column=Column("CategoriaId", Integer, ForeignKey("Categorias_Ingredientes.Id"), nullable=False)
    )
    nombre: str = Field(sa_column=Column("Nombre", String(150), nullable=False))
    descripcion: Optional[str] = Field(default=None, sa_column=Column("Descripcion", String(500)))
    # Canonical storage unit for this ingredient
    unidad_medida: str = Field(sa_column=Column("UnidadMedida", String(20), nullable=False))
    cantidad_actual: Decimal = Field(
        default=Decimal("0"),
        sa_column=Column("CantidadActual", Numeric(12, 4), nullable=False, server_default=text("0"))
    )
    cantidad_minima: Decimal = Field(
        default=Decimal("0"),
        sa_column=Column("CantidadMinima", Numeric(12, 4), nullable=False, server_default=text("0"))
    )
    cantidad_reorden: Decimal = Field(
        default=Decimal("0"),
        sa_column=Column("CantidadReorden", Numeric(12, 4), nullable=False, server_default=text("0"))
    )
    costo_unitario: Decimal = Field(
        default=Decimal("0"),
        sa_column=Column("CostoUnitario", Numeric(12, 4), nullable=False, server_default=text("0"))
    )
    activo: bool = Field(default=True, sa_column=Column("Activo", Boolean, nullable=False, server_default=text("1")))
    ultima_modificacion: datetime = Field(
        sa_column=Column("Ultima_Modificacion", DateTime, nullable=False, server_default=text("GETDATE()"))
    )


class RecetaProducto(SQLModel, table=True):
    """
    BOM Header: one recipe per product.
    A product must have tipo_control_inventario = 'INGREDIENTES' to use this.
    """
    __tablename__ = "Recetas_Producto"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    producto_id: int = Field(
        sa_column=Column("ProductoId", Integer, ForeignKey("Productos.Id"), unique=True, nullable=False)
    )
    descripcion: Optional[str] = Field(default=None, sa_column=Column("Descripcion", String(500)))
    activo: bool = Field(default=True, sa_column=Column("Activo", Boolean, nullable=False, server_default=text("1")))
    ultima_modificacion: datetime = Field(
        sa_column=Column("Ultima_Modificacion", DateTime, nullable=False, server_default=text("GETDATE()"))
    )


class ComponenteReceta(SQLModel, table=True):
    """
    BOM Line: each ingredient required and the amount needed to produce ONE unit of the product.
    UnidadMedida may differ from the ingredient's canonical unit — conversion is applied at runtime.
    """
    __tablename__ = "Componentes_Receta"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    receta_id: int = Field(
        sa_column=Column("RecetaId", Integer, ForeignKey("Recetas_Producto.Id"), nullable=False)
    )
    ingrediente_id: int = Field(
        sa_column=Column("IngredienteId", Integer, ForeignKey("Ingredientes.Id"), nullable=False)
    )
    # Quantity of this ingredient required to make ONE unit of the product
    cantidad_requerida: Decimal = Field(
        sa_column=Column("CantidadRequerida", Numeric(12, 4), nullable=False)
    )
    # Unit in which the recipe specifies the quantity (may differ from ingredient's storage unit)
    unidad_medida: str = Field(sa_column=Column("UnidadMedida", String(20), nullable=False))


class MovimientoIngrediente(SQLModel, table=True):
    """
    Full audit ledger for every ingredient stock change.
    Replaces (for ingredient-based products) the legacy Movimientos_Inventario table.

    TipoMovimiento values:
        COMPRA          - Stock purchased/received
        AJUSTE_MANUAL   - Manual stock adjustment (delta)
        CONSUMO_VENTA   - Auto-deducted when an order is created
        DESPERDICIO     - Waste/spoilage write-off
        CORRECCION      - Physical count correction (sets absolute value)
        CARGA_INICIAL   - Initial stock load
        DEVOLUCION      - Reversal on order cancellation
    """
    __tablename__ = "Movimientos_Ingrediente"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    ingrediente_id: int = Field(
        sa_column=Column("IngredienteId", Integer, ForeignKey("Ingredientes.Id"), nullable=False)
    )
    empleado_id: Optional[int] = Field(
        default=None, sa_column=Column("EmpleadoId", Integer, ForeignKey("Empleados.Id"))
    )
    tipo_movimiento: str = Field(sa_column=Column("TipoMovimiento", String(30), nullable=False))
    # Delta quantity (absolute value for CORRECCION)
    cantidad: Decimal = Field(sa_column=Column("Cantidad", Numeric(12, 4), nullable=False))
    cantidad_anterior: Decimal = Field(sa_column=Column("CantidadAnterior", Numeric(12, 4), nullable=False))
    cantidad_nueva: Decimal = Field(sa_column=Column("CantidadNueva", Numeric(12, 4), nullable=False))
    documento_referencia: Optional[str] = Field(
        default=None, sa_column=Column("DocumentoReferencia", String(100))
    )
    pedido_id: Optional[int] = Field(
        default=None, sa_column=Column("PedidoId", Integer, ForeignKey("Pedidos_Global.Id"))
    )
    notas: Optional[str] = Field(default=None, sa_column=Column("Notas", String(500)))
    fecha_movimiento: datetime = Field(
        sa_column=Column("FechaMovimiento", DateTime, nullable=False, server_default=text("GETDATE()"))
    )
    movimiento_local_uuid: Optional[str] = Field(
        default=None, sa_column=Column("Movimiento_Local_UUID", String(36))
    )


# ─────────────────────────────────────────────────────────────────
# SISTEMA DE PROMOCIONES EXTENDIDO
# ─────────────────────────────────────────────────────────────────

class CodigoPromocional(SQLModel, table=True):
    """Promo codes linked to a promotion (Codigos_Promocionales table)."""
    __tablename__ = "Codigos_Promocionales"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    promocion_id: int = Field(sa_column=Column("PromocionId", Integer, ForeignKey("Promociones.Id"), nullable=False))
    codigo: str = Field(sa_column=Column("Codigo", String(50), unique=True, nullable=False))
    fecha_inicio: datetime = Field(sa_column=Column("FechaInicio", DateTime, nullable=False))
    fecha_fin: Optional[datetime] = Field(default=None, sa_column=Column("FechaFin", DateTime))
    uso_maximo: Optional[int] = Field(default=None, sa_column=Column("UsoMaximo", Integer))
    usos_actuales: int = Field(default=0, sa_column=Column("UsosActuales", Integer, nullable=False, server_default=text("0")))
    un_uso_por_cliente: bool = Field(default=False, sa_column=Column("UnUsoPorCliente", Boolean, nullable=False, server_default=text("0")))
    cliente_especifico_id: Optional[int] = Field(default=None, sa_column=Column("ClienteEspecificoId", Integer, ForeignKey("Clientes.Id")))
    monto_minimo_compra: Optional[Decimal] = Field(default=None, sa_column=Column("MontoMinimoCompra", Numeric(12, 2)))
    activo: bool = Field(default=True, sa_column=Column("Activo", Boolean, nullable=False, server_default=text("1")))
    fecha_creacion: datetime = Field(sa_column=Column("FechaCreacion", DateTime, nullable=False, server_default=text("GETDATE()")))


class PromocionElegibilidad(SQLModel, table=True):
    """Eligibility config for ELEGIBILIDAD-type promotions (Promociones_Elegibilidad table)."""
    __tablename__ = "Promociones_Elegibilidad"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", Integer, primary_key=True))
    promocion_id: int = Field(sa_column=Column("PromocionId", Integer, ForeignKey("Promociones.Id"), unique=True, nullable=False))
    etiqueta_identificador: str = Field(
        default="Credential ID",
        sa_column=Column("EtiquetaIdentificador", String(100), nullable=False, server_default=text("'Credential ID'"))
    )
    requiere_identificador: bool = Field(
        default=True,
        sa_column=Column("RequiereIdentificador", Boolean, nullable=False, server_default=text("1"))
    )


class AplicacionPromocion(SQLModel, table=True):
    """Immutable audit ledger for every promotion application (Aplicaciones_Promocion table)."""
    __tablename__ = "Aplicaciones_Promocion"
    id: Optional[int] = Field(default=None, sa_column=Column("Id", BigInteger, primary_key=True))
    promocion_id: Optional[int] = Field(default=None, sa_column=Column("PromocionId", Integer, ForeignKey("Promociones.Id")))
    nombre_promocion_snap: str = Field(sa_column=Column("NombrePromocionSnap", String(150), nullable=False))
    tipo_aplicacion: str = Field(sa_column=Column("TipoAplicacion", String(20), nullable=False))
    pedido_id: Optional[int] = Field(default=None, sa_column=Column("PedidoId", Integer, ForeignKey("Pedidos_Global.Id")))
    factura_uuid: Optional[uuid.UUID] = Field(default=None, sa_column=Column("FacturaUUID", UNIQUEIDENTIFIER))
    empleado_id: Optional[int] = Field(default=None, sa_column=Column("EmpleadoId", Integer, ForeignKey("Empleados.Id")))
    empleado_autorizador_id: Optional[int] = Field(default=None, sa_column=Column("EmpleadoAutorizadorId", Integer, ForeignKey("Empleados.Id")))
    cliente_id: Optional[int] = Field(default=None, sa_column=Column("ClienteId", Integer, ForeignKey("Clientes.Id")))
    identificador_capturado: Optional[str] = Field(default=None, sa_column=Column("IdentificadorCapturado", String(255)))
    monto_descuento: Decimal = Field(default=Decimal("0"), sa_column=Column("MontoDescuento", Numeric(12, 2), nullable=False, server_default=text("0")))
    terminal: Optional[str] = Field(default=None, sa_column=Column("Terminal", String(50)))
    notas: Optional[str] = Field(default=None, sa_column=Column("Notas", String(500)))
    fecha_hora: datetime = Field(sa_column=Column("FechaHora", DateTime, nullable=False, server_default=text("GETDATE()")))


class SupervisorSessionAudit(SQLModel, table=True):
    """Audit record for supervisor sessions synced from CAJA (SupervisorSessionAudit table)."""
    __tablename__ = "SupervisorSessionAudit"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=Column("id", UNIQUEIDENTIFIER, primary_key=True))
    supervisor_id: int = Field(sa_column=Column("supervisor_id", Integer, ForeignKey("Empleados.Id"), nullable=False))
    cajero_id: int = Field(sa_column=Column("cajero_id", Integer, ForeignKey("Empleados.Id"), nullable=False))
    terminal: str = Field(sa_column=Column("terminal", String(50), nullable=False))
    inicio: datetime = Field(sa_column=Column("inicio", DateTime, nullable=False))
    fin: datetime = Field(sa_column=Column("fin", DateTime, nullable=False))
    motivo_fin: str = Field(sa_column=Column("motivo_fin", String(50), nullable=False))
