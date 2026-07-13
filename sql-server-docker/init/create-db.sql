-- ═════════════════════════════════════════════════════════════════
-- Core_Master_DB — Script completo v3
-- Idempotente: seguro para ejecutar múltiples veces
-- ═════════════════════════════════════════════════════════════════

IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = N'Core_Master_DB')
BEGIN
    CREATE DATABASE Core_Master_DB;
END
GO

USE Core_Master_DB;
GO

-- ─────────────────────────────────────────────────────────────────
-- TABLAS BASE (sin dependencias)
-- ─────────────────────────────────────────────────────────────────

IF OBJECT_ID('dbo.Sucursales', 'U') IS NULL
BEGIN
    CREATE TABLE Sucursales (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        Nombre NVARCHAR(100) NOT NULL,
        Direccion NVARCHAR(255) NULL,
        Activo BIT NOT NULL DEFAULT 1
    );
END
GO

IF OBJECT_ID('dbo.Roles', 'U') IS NULL
BEGIN
    CREATE TABLE Roles (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        Nombre NVARCHAR(50) NOT NULL UNIQUE
    );
END
GO

IF OBJECT_ID('dbo.Clientes', 'U') IS NULL
BEGIN
    CREATE TABLE Clientes (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        NombreCompleto NVARCHAR(150) NOT NULL,
        Email NVARCHAR(150) NOT NULL UNIQUE,
        Telefono NVARCHAR(20) NULL,
        PasswordHash NVARCHAR(255) NOT NULL,
        FechaRegistro DATETIME NOT NULL DEFAULT GETDATE(),
        Activo BIT NOT NULL DEFAULT 1
    );
END
GO

IF OBJECT_ID('dbo.Impuestos', 'U') IS NULL
BEGIN
    CREATE TABLE Impuestos (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        Nombre NVARCHAR(50) NOT NULL UNIQUE,
        TasaPorcentaje NUMERIC(5,2) NOT NULL,
        Activo BIT NOT NULL DEFAULT 1,
        Ultima_Modificacion DATETIME NOT NULL DEFAULT GETDATE()
    );
END
GO

IF OBJECT_ID('dbo.Categorias', 'U') IS NULL
BEGIN
    CREATE TABLE Categorias (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        Nombre NVARCHAR(100) NOT NULL UNIQUE,
        Descripcion NVARCHAR(255) NULL,
        Activo BIT NOT NULL DEFAULT 1,
        Ultima_Modificacion DATETIME NOT NULL DEFAULT GETDATE()
    );
END
GO

IF OBJECT_ID('dbo.Mesas', 'U') IS NULL
BEGIN
    CREATE TABLE Mesas (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        Numero INT NOT NULL UNIQUE,
        Descripcion NVARCHAR(255) NULL,
        Capacidad INT NOT NULL DEFAULT 4,
        Activo BIT NOT NULL DEFAULT 1,
        QrToken NVARCHAR(100) NULL,
        FechaCreacion DATETIME NOT NULL DEFAULT GETDATE()
    );
END
GO

IF OBJECT_ID('dbo.Core_Logs', 'U') IS NULL
BEGIN
    CREATE TABLE Core_Logs (
        Log_Id INT IDENTITY(1,1) PRIMARY KEY,
        Fecha_Hora DATETIME NOT NULL DEFAULT GETDATE(),
        Nivel NVARCHAR(20) NOT NULL,
        Origen NVARCHAR(100) NOT NULL,
        Mensaje NVARCHAR(MAX) NOT NULL,
        Data_JSON NVARCHAR(MAX) NULL
    );
END
GO

IF OBJECT_ID('dbo.Password_Reset_Tokens', 'U') IS NULL
BEGIN
    CREATE TABLE Password_Reset_Tokens (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        TokenHash NVARCHAR(255) NOT NULL,
        EntidadTipo NVARCHAR(20) NOT NULL,
        EntidadId INT NOT NULL,
        ExpiraEn DATETIME NOT NULL,
        Usado BIT NOT NULL DEFAULT 0,
        FechaCreacion DATETIME NOT NULL DEFAULT GETDATE()
    );
    CREATE INDEX IX_Password_Reset_Tokens_TokenHash ON Password_Reset_Tokens(TokenHash);
END
GO

-- ─────────────────────────────────────────────────────────────────
-- SISTEMA DE INVENTARIO POR INGREDIENTES — TABLAS BASE
-- ─────────────────────────────────────────────────────────────────

IF OBJECT_ID('dbo.Categorias_Ingredientes', 'U') IS NULL
BEGIN
    CREATE TABLE Categorias_Ingredientes (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        Nombre NVARCHAR(100) NOT NULL UNIQUE,
        Descripcion NVARCHAR(500) NULL,
        Activo BIT NOT NULL DEFAULT 1,
        Ultima_Modificacion DATETIME NOT NULL DEFAULT GETDATE()
    );
END
GO

-- ─────────────────────────────────────────────────────────────────
-- TABLAS CON DEPENDENCIA DE NIVEL 1
-- ─────────────────────────────────────────────────────────────────

IF OBJECT_ID('dbo.Empleados', 'U') IS NULL
BEGIN
    CREATE TABLE Empleados (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        RolId INT NOT NULL,
        SucursalId INT NOT NULL,
        DocumentoIdentidad NVARCHAR(20) NOT NULL UNIQUE,
        NombreCompleto NVARCHAR(150) NOT NULL,
        Email NVARCHAR(150) NOT NULL UNIQUE,
        PasswordHash NVARCHAR(255) NOT NULL,
        Activo BIT NOT NULL DEFAULT 1,
        CONSTRAINT FK_Empleados_Roles FOREIGN KEY (RolId) REFERENCES Roles(Id),
        CONSTRAINT FK_Empleados_Sucursales FOREIGN KEY (SucursalId) REFERENCES Sucursales(Id)
    );
END
GO

IF OBJECT_ID('dbo.Productos', 'U') IS NULL
BEGIN
    CREATE TABLE Productos (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        CategoriaId INT NOT NULL,
        ImpuestoId INT NOT NULL,
        SKU NVARCHAR(50) NOT NULL UNIQUE,
        Nombre NVARCHAR(150) NOT NULL,
        Descripcion NVARCHAR(1000) NULL,
        PrecioBase NUMERIC(12,2) NOT NULL,
        CostoPromedio NUMERIC(12,2) NOT NULL DEFAULT 0,
        -- PRODUCTO = control unitario | INGREDIENTES = basado en receta | NINGUNO = sin control
        TipoControlInventario NVARCHAR(20) NOT NULL DEFAULT 'PRODUCTO',
        Activo BIT NOT NULL DEFAULT 1,
        Ultima_Modificacion DATETIME NULL DEFAULT GETDATE(),
        ImagenURL NVARCHAR(1000) NULL,
        CONSTRAINT FK_Productos_Categorias FOREIGN KEY (CategoriaId) REFERENCES Categorias(Id),
        CONSTRAINT FK_Productos_Impuestos FOREIGN KEY (ImpuestoId) REFERENCES Impuestos(Id)
    );
END
GO

-- Migración: tabla Productos ya existe con schema viejo
IF EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('dbo.Productos') AND name = 'EsInventariable'
)
BEGIN
    ALTER TABLE dbo.Productos DROP COLUMN EsInventariable;
    PRINT 'Columna EsInventariable eliminada de Productos.';
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('dbo.Productos') AND name = 'TipoControlInventario'
)
BEGIN
    ALTER TABLE dbo.Productos
    ADD TipoControlInventario NVARCHAR(20) NOT NULL DEFAULT 'PRODUCTO';
    PRINT 'Columna TipoControlInventario agregada a Productos.';
END
GO

IF OBJECT_ID('dbo.Ingredientes', 'U') IS NULL
BEGIN
    -- UnidadMedida valores: ml | l | g | kg | unidad | pieza | botella | lata
    CREATE TABLE Ingredientes (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        CategoriaId INT NOT NULL,
        Nombre NVARCHAR(150) NOT NULL,
        Descripcion NVARCHAR(500) NULL,
        UnidadMedida NVARCHAR(20) NOT NULL,
        CantidadActual NUMERIC(12,4) NOT NULL DEFAULT 0,
        CantidadMinima NUMERIC(12,4) NOT NULL DEFAULT 0,
        CantidadReorden NUMERIC(12,4) NOT NULL DEFAULT 0,
        CostoUnitario NUMERIC(12,4) NOT NULL DEFAULT 0,
        Activo BIT NOT NULL DEFAULT 1,
        Ultima_Modificacion DATETIME NOT NULL DEFAULT GETDATE(),
        CONSTRAINT FK_Ingredientes_CategoriasIngredientes FOREIGN KEY (CategoriaId) REFERENCES Categorias_Ingredientes(Id)
    );
END
GO

IF OBJECT_ID('dbo.Secuencias_NCF', 'U') IS NULL
BEGIN
    CREATE TABLE Secuencias_NCF (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        TipoNcf NVARCHAR(10) NOT NULL,
        Serie NVARCHAR(10) NOT NULL,
        RangoDesde INT NOT NULL,
        RangoHasta INT NOT NULL,
        SecuenciaActual INT NOT NULL,
        FechaVencimiento DATETIME NOT NULL,
        Activo BIT NOT NULL DEFAULT 1,
        SucursalId INT NULL,
        FechaCreacion DATETIME NOT NULL DEFAULT GETDATE(),
        CONSTRAINT FK_SecuenciasNCF_Sucursales FOREIGN KEY (SucursalId) REFERENCES Sucursales(Id)
    );
END
GO

IF OBJECT_ID('dbo.Promociones', 'U') IS NULL
BEGIN
    CREATE TABLE Promociones (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        Nombre NVARCHAR(150) NOT NULL UNIQUE,
        Descripcion NVARCHAR(500) NULL,
        TipoDescuento NVARCHAR(20) NOT NULL,
        Valor NUMERIC(12,2) NOT NULL,
        FechaInicio DATETIME NOT NULL,
        FechaFin DATETIME NULL,
        Activo BIT NOT NULL DEFAULT 1,
        Prioridad INT NOT NULL DEFAULT 0,
        AplicaA NVARCHAR(20) NOT NULL DEFAULT 'TODOS',
        -- AUTOMATICA | ELEGIBILIDAD | CODIGO_PROMO | MANUAL
        TipoAplicacion NVARCHAR(20) NOT NULL DEFAULT 'AUTOMATICA',
        AplicaHappyHour BIT NOT NULL DEFAULT 0,
        HoraInicioHH NVARCHAR(5) NULL,
        HoraFinHH NVARCHAR(5) NULL,
        PrecioMinimoFinal NUMERIC(12,2) NULL,
        FechaCreacion DATETIME NOT NULL DEFAULT GETDATE()
    );
END
GO

-- Migración: Promociones ya existe sin columnas del sistema extendido
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('dbo.Promociones') AND name = 'TipoAplicacion'
)
BEGIN
    ALTER TABLE dbo.Promociones
    ADD TipoAplicacion NVARCHAR(20) NOT NULL DEFAULT 'AUTOMATICA';
    PRINT 'Columna TipoAplicacion agregada a Promociones.';
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('dbo.Promociones') AND name = 'PrecioMinimoFinal'
)
BEGIN
    ALTER TABLE dbo.Promociones
    ADD PrecioMinimoFinal NUMERIC(12,2) NULL;
    PRINT 'Columna PrecioMinimoFinal agregada a Promociones.';
END
GO

-- ─────────────────────────────────────────────────────────────────
-- TABLAS CON DEPENDENCIA DE NIVEL 2
-- ─────────────────────────────────────────────────────────────────

IF OBJECT_ID('dbo.Inventario_Actual', 'U') IS NULL
BEGIN
    CREATE TABLE Inventario_Actual (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        ProductoId INT NOT NULL UNIQUE,
        CantidadDisponible INT NOT NULL DEFAULT 0,
        StockMinimo INT NOT NULL DEFAULT 5,
        UltimaActualizacion DATETIME NULL DEFAULT GETDATE(),
        Ultima_Modificacion DATETIME NULL DEFAULT GETDATE(),
        CONSTRAINT FK_InventarioActual_Productos FOREIGN KEY (ProductoId) REFERENCES Productos(Id)
    );
END
GO

IF OBJECT_ID('dbo.Movimientos_Inventario', 'U') IS NULL
BEGIN
    CREATE TABLE Movimientos_Inventario (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        ProductoId INT NOT NULL,
        EmpleadoId INT NULL,
        TipoMovimiento NVARCHAR(20) NOT NULL,
        Cantidad INT NOT NULL,
        Motivo NVARCHAR(255) NOT NULL,
        FechaMovimiento DATETIME NULL DEFAULT GETDATE(),
        movimiento_local_uuid NVARCHAR(255) NULL,
        Factura_Local_UUID UNIQUEIDENTIFIER NULL,
        CONSTRAINT FK_MovimientosInventario_Productos FOREIGN KEY (ProductoId) REFERENCES Productos(Id),
        CONSTRAINT FK_MovimientosInventario_Empleados FOREIGN KEY (EmpleadoId) REFERENCES Empleados(Id)
    );
END
GO

IF OBJECT_ID('dbo.Pedidos_Global', 'U') IS NULL
BEGIN
    CREATE TABLE Pedidos_Global (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        ClienteId INT NULL,
        EmpleadoId INT NULL,
        Mesa NVARCHAR(50) NULL,
        CanalOrigen NVARCHAR(50) NOT NULL,
        Estado NVARCHAR(50) NOT NULL DEFAULT 'PENDIENTE',
        Subtotal NUMERIC(12,2) NOT NULL DEFAULT 0,
        TotalImpuestos NUMERIC(12,2) NOT NULL DEFAULT 0,
        PropinaLegal NUMERIC(12,2) NULL DEFAULT 0,
        TotalGeneral NUMERIC(12,2) NOT NULL DEFAULT 0,
        FechaCreacion DATETIME NULL DEFAULT GETDATE(),
        Factura_Local_UUID UNIQUEIDENTIFIER NULL,
        PropinaExtra NUMERIC(12,2) NOT NULL DEFAULT 0,
        CONSTRAINT FK_PedidosGlobal_Clientes FOREIGN KEY (ClienteId) REFERENCES Clientes(Id),
        CONSTRAINT FK_PedidosGlobal_Empleados FOREIGN KEY (EmpleadoId) REFERENCES Empleados(Id)
    );
    CREATE INDEX IX_Pedidos_Global_Factura_Local_UUID ON Pedidos_Global(Factura_Local_UUID);
END
GO

IF OBJECT_ID('dbo.Aplicaciones_Promocion', 'U') IS NULL
BEGIN
    -- Ledger inmutable de cada aplicación de promoción (sync desde CAJA)
    CREATE TABLE Aplicaciones_Promocion (
        Id BIGINT IDENTITY(1,1) PRIMARY KEY,
        PromocionId INT NULL,
        NombrePromocionSnap NVARCHAR(150) NOT NULL,
        TipoAplicacion NVARCHAR(20) NOT NULL,
        PedidoId INT NULL,
        FacturaUUID UNIQUEIDENTIFIER NULL,
        EmpleadoId INT NULL,
        EmpleadoAutorizadorId INT NULL,
        ClienteId INT NULL,
        IdentificadorCapturado NVARCHAR(255) NULL,
        MontoDescuento NUMERIC(12,2) NOT NULL DEFAULT 0,
        Terminal NVARCHAR(50) NULL,
        Notas NVARCHAR(500) NULL,
        FechaHora DATETIME NOT NULL DEFAULT GETDATE(),
        CONSTRAINT FK_AplicacionesPromocion_Promociones FOREIGN KEY (PromocionId) REFERENCES Promociones(Id),
        CONSTRAINT FK_AplicacionesPromocion_PedidosGlobal FOREIGN KEY (PedidoId) REFERENCES Pedidos_Global(Id),
        CONSTRAINT FK_AplicacionesPromocion_Empleados FOREIGN KEY (EmpleadoId) REFERENCES Empleados(Id),
        CONSTRAINT FK_AplicacionesPromocion_EmpleadosAutorizador FOREIGN KEY (EmpleadoAutorizadorId) REFERENCES Empleados(Id),
        CONSTRAINT FK_AplicacionesPromocion_Clientes FOREIGN KEY (ClienteId) REFERENCES Clientes(Id)
    );
END
GO

IF OBJECT_ID('dbo.SupervisorSessionAudit', 'U') IS NULL
BEGIN
    -- Auditoría de sesiones de supervisor sincronizadas desde CAJA
    CREATE TABLE SupervisorSessionAudit (
        id UNIQUEIDENTIFIER NOT NULL PRIMARY KEY DEFAULT NEWID(),
        supervisor_id INT NOT NULL,
        cajero_id INT NOT NULL,
        terminal NVARCHAR(50) NOT NULL,
        inicio DATETIME NOT NULL,
        fin DATETIME NOT NULL,
        motivo_fin NVARCHAR(50) NOT NULL,
        CONSTRAINT FK_SupervisorSessionAudit_Supervisor FOREIGN KEY (supervisor_id) REFERENCES Empleados(Id),
        CONSTRAINT FK_SupervisorSessionAudit_Cajero FOREIGN KEY (cajero_id) REFERENCES Empleados(Id)
    );
END
GO

IF OBJECT_ID('dbo.Promociones_Productos', 'U') IS NULL
BEGIN
    CREATE TABLE Promociones_Productos (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        PromocionId INT NOT NULL,
        ProductoId INT NOT NULL,
        CONSTRAINT FK_PromocionesProductos_Promociones FOREIGN KEY (PromocionId) REFERENCES Promociones(Id),
        CONSTRAINT FK_PromocionesProductos_Productos FOREIGN KEY (ProductoId) REFERENCES Productos(Id)
    );
END
GO

IF OBJECT_ID('dbo.Promociones_Categorias', 'U') IS NULL
BEGIN
    CREATE TABLE Promociones_Categorias (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        PromocionId INT NOT NULL,
        CategoriaId INT NOT NULL,
        CONSTRAINT FK_PromocionesCategorias_Promociones FOREIGN KEY (PromocionId) REFERENCES Promociones(Id),
        CONSTRAINT FK_PromocionesCategorias_Categorias FOREIGN KEY (CategoriaId) REFERENCES Categorias(Id)
    );
END
GO

-- ─────────────────────────────────────────────────────────────────
-- SISTEMA DE PROMOCIONES EXTENDIDO — TABLAS BASE
-- ─────────────────────────────────────────────────────────────────

IF OBJECT_ID('dbo.Codigos_Promocionales', 'U') IS NULL
BEGIN
    CREATE TABLE Codigos_Promocionales (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        PromocionId INT NOT NULL,
        Codigo NVARCHAR(50) NOT NULL UNIQUE,
        FechaInicio DATETIME NOT NULL,
        FechaFin DATETIME NULL,
        UsoMaximo INT NULL,
        UsosActuales INT NOT NULL DEFAULT 0,
        UnUsoPorCliente BIT NOT NULL DEFAULT 0,
        ClienteEspecificoId INT NULL,
        MontoMinimoCompra NUMERIC(12,2) NULL,
        Activo BIT NOT NULL DEFAULT 1,
        FechaCreacion DATETIME NOT NULL DEFAULT GETDATE(),
        CONSTRAINT FK_CodigosPromocionales_Promociones FOREIGN KEY (PromocionId) REFERENCES Promociones(Id),
        CONSTRAINT FK_CodigosPromocionales_Clientes FOREIGN KEY (ClienteEspecificoId) REFERENCES Clientes(Id)
    );
END
GO

IF OBJECT_ID('dbo.Promociones_Elegibilidad', 'U') IS NULL
BEGIN
    CREATE TABLE Promociones_Elegibilidad (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        PromocionId INT NOT NULL UNIQUE,
        EtiquetaIdentificador NVARCHAR(100) NOT NULL DEFAULT 'Credential ID',
        RequiereIdentificador BIT NOT NULL DEFAULT 1,
        CONSTRAINT FK_PromocionesElegibilidad_Promociones FOREIGN KEY (PromocionId) REFERENCES Promociones(Id)
    );
END
GO

IF OBJECT_ID('dbo.Recetas_Producto', 'U') IS NULL
BEGIN
    -- BOM Header: una receta por producto (requiere TipoControlInventario = 'INGREDIENTES')
    CREATE TABLE Recetas_Producto (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        ProductoId INT NOT NULL UNIQUE,
        Descripcion NVARCHAR(500) NULL,
        Activo BIT NOT NULL DEFAULT 1,
        Ultima_Modificacion DATETIME NOT NULL DEFAULT GETDATE(),
        CONSTRAINT FK_RecetasProducto_Productos FOREIGN KEY (ProductoId) REFERENCES Productos(Id)
    );
END
GO

-- ─────────────────────────────────────────────────────────────────
-- TABLAS CON DEPENDENCIA DE NIVEL 3
-- ─────────────────────────────────────────────────────────────────

IF OBJECT_ID('dbo.Detalles_Pedido', 'U') IS NULL
BEGIN
    CREATE TABLE Detalles_Pedido (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        PedidoId INT NOT NULL,
        ProductoId INT NOT NULL,
        Cantidad INT NOT NULL,
        PrecioUnitarioHistorico NUMERIC(12,2) NOT NULL,
        ImpuestoHistorico NUMERIC(5,2) NOT NULL,
        MontoImpuesto NUMERIC(12,2) NOT NULL DEFAULT 0,
        SubtotalLinea NUMERIC(12,2) NOT NULL DEFAULT 0,
        Detalle_Local_UUID UNIQUEIDENTIFIER NULL,
        CONSTRAINT FK_DetallesPedido_PedidosGlobal FOREIGN KEY (PedidoId) REFERENCES Pedidos_Global(Id),
        CONSTRAINT FK_DetallesPedido_Productos FOREIGN KEY (ProductoId) REFERENCES Productos(Id)
    );
END
GO

IF OBJECT_ID('dbo.Historial_NCF', 'U') IS NULL
BEGIN
    CREATE TABLE Historial_NCF (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        SecuenciaId INT NOT NULL,
        NcfAsignado NVARCHAR(20) NOT NULL,
        PedidoId INT NULL,
        EmpleadoId INT NULL,
        FechaAsignacion DATETIME NOT NULL DEFAULT GETDATE(),
        CONSTRAINT FK_HistorialNCF_SecuenciasNCF FOREIGN KEY (SecuenciaId) REFERENCES Secuencias_NCF(Id),
        CONSTRAINT FK_HistorialNCF_PedidosGlobal FOREIGN KEY (PedidoId) REFERENCES Pedidos_Global(Id),
        CONSTRAINT FK_HistorialNCF_Empleados FOREIGN KEY (EmpleadoId) REFERENCES Empleados(Id)
    );
END
GO

IF OBJECT_ID('dbo.Division_Cuenta', 'U') IS NULL
BEGIN
    CREATE TABLE Division_Cuenta (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        PedidoId INT NOT NULL,
        NumeroPartes INT NOT NULL,
        MontoPorParte NUMERIC(12,2) NOT NULL,
        MontosPersonalizadosJson NVARCHAR(2000) NULL,
        EmpleadoId INT NULL,
        FechaDivision DATETIME NOT NULL DEFAULT GETDATE(),
        CONSTRAINT FK_DivisionCuenta_PedidosGlobal FOREIGN KEY (PedidoId) REFERENCES Pedidos_Global(Id),
        CONSTRAINT FK_DivisionCuenta_Empleados FOREIGN KEY (EmpleadoId) REFERENCES Empleados(Id)
    );
END
GO

IF OBJECT_ID('dbo.Componentes_Receta', 'U') IS NULL
BEGIN
    -- BOM Line: ingrediente + cantidad necesaria para producir UNA unidad del producto
    -- UnidadMedida puede diferir de la unidad canónica del ingrediente (conversión en runtime)
    CREATE TABLE Componentes_Receta (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        RecetaId INT NOT NULL,
        IngredienteId INT NOT NULL,
        CantidadRequerida NUMERIC(12,4) NOT NULL,
        UnidadMedida NVARCHAR(20) NOT NULL,
        CONSTRAINT FK_ComponentesReceta_RecetasProducto FOREIGN KEY (RecetaId) REFERENCES Recetas_Producto(Id),
        CONSTRAINT FK_ComponentesReceta_Ingredientes FOREIGN KEY (IngredienteId) REFERENCES Ingredientes(Id)
    );
END
GO

IF OBJECT_ID('dbo.Movimientos_Ingrediente', 'U') IS NULL
BEGIN
    /*
      TipoMovimiento valores:
        COMPRA          - Stock comprado/recibido
        AJUSTE_MANUAL   - Ajuste manual de stock (delta)
        CONSUMO_VENTA   - Deducción automática al crear un pedido
        DESPERDICIO     - Baja por desperdicio o merma
        CORRECCION      - Corrección por conteo físico (valor absoluto)
        CARGA_INICIAL   - Carga inicial de stock
        DEVOLUCION      - Reversión por cancelación de pedido
    */
    CREATE TABLE Movimientos_Ingrediente (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        IngredienteId INT NOT NULL,
        EmpleadoId INT NULL,
        TipoMovimiento NVARCHAR(30) NOT NULL,
        Cantidad NUMERIC(12,4) NOT NULL,
        CantidadAnterior NUMERIC(12,4) NOT NULL,
        CantidadNueva NUMERIC(12,4) NOT NULL,
        DocumentoReferencia NVARCHAR(100) NULL,
        PedidoId INT NULL,
        Notas NVARCHAR(500) NULL,
        FechaMovimiento DATETIME NOT NULL DEFAULT GETDATE(),
        Movimiento_Local_UUID NVARCHAR(36) NULL,
        CONSTRAINT FK_MovimientosIngrediente_Ingredientes  FOREIGN KEY (IngredienteId) REFERENCES Ingredientes(Id),
        CONSTRAINT FK_MovimientosIngrediente_Empleados     FOREIGN KEY (EmpleadoId)    REFERENCES Empleados(Id),
        CONSTRAINT FK_MovimientosIngrediente_PedidosGlobal FOREIGN KEY (PedidoId)      REFERENCES Pedidos_Global(Id)
    );
END
GO

-- ─────────────────────────────────────────────────────────────────
-- TABLAS CON DEPENDENCIA DE NIVEL 4
-- ─────────────────────────────────────────────────────────────────

IF OBJECT_ID('dbo.Modificadores_Item', 'U') IS NULL
BEGIN
    -- Referencia al detalle via UUID (desacoplado, sin FK directa)
    CREATE TABLE Modificadores_Item (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        DetallePedidoUuid UNIQUEIDENTIFIER NOT NULL,
        Descripcion NVARCHAR(255) NOT NULL,
        FechaRegistro DATETIME NULL DEFAULT GETDATE()
    );
    CREATE INDEX IX_Modificadores_Item_DetallePedidoUuid ON Modificadores_Item(DetallePedidoUuid);
END
GO

-- Migración: tabla Modificadores_Item ya existe con schema viejo (DetallePedidoId INT)
IF EXISTS (
    SELECT 1 FROM sys.foreign_keys
    WHERE name = 'FK_ModificadoresItem_DetallesPedido'
)
BEGIN
    ALTER TABLE dbo.Modificadores_Item DROP CONSTRAINT FK_ModificadoresItem_DetallesPedido;
    PRINT 'FK FK_ModificadoresItem_DetallesPedido eliminada.';
END
GO

IF EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID('dbo.Modificadores_Item')
    AND name = 'IX_Modificadores_Item_DetallePedidoId'
)
BEGIN
    DROP INDEX IX_Modificadores_Item_DetallePedidoId ON dbo.Modificadores_Item;
    PRINT 'Índice IX_Modificadores_Item_DetallePedidoId eliminado.';
END
GO

IF EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('dbo.Modificadores_Item') AND name = 'DetallePedidoId'
)
BEGIN
    ALTER TABLE dbo.Modificadores_Item DROP COLUMN DetallePedidoId;
    PRINT 'Columna DetallePedidoId eliminada de Modificadores_Item.';
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('dbo.Modificadores_Item') AND name = 'DetallePedidoUuid'
)
BEGIN
    ALTER TABLE dbo.Modificadores_Item ADD DetallePedidoUuid UNIQUEIDENTIFIER NULL;
    UPDATE dbo.Modificadores_Item SET DetallePedidoUuid = NEWID() WHERE DetallePedidoUuid IS NULL;
    ALTER TABLE dbo.Modificadores_Item ALTER COLUMN DetallePedidoUuid UNIQUEIDENTIFIER NOT NULL;
    CREATE INDEX IX_Modificadores_Item_DetallePedidoUuid ON dbo.Modificadores_Item(DetallePedidoUuid);
    PRINT 'Columna DetallePedidoUuid agregada a Modificadores_Item.';
END
GO

PRINT '✔ Todas las tablas creadas/migradas correctamente (v3 — promociones extendido).';
GO


-- ═════════════════════════════════════════════════════════════════
-- SEED: INSERCIÓN DE DATOS DE PRUEBA (idempotente)
-- ═════════════════════════════════════════════════════════════════

USE Core_Master_DB;
GO

-- ─────────────────────────────────────────────────────────────────
-- Sucursales
-- ─────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM dbo.Sucursales WHERE Nombre = 'Sucursal Naco')
    INSERT INTO dbo.Sucursales (Nombre, Direccion, Activo) VALUES
    ('Sucursal Naco',       'Av. Tiradentes #45, Naco, Santo Domingo', 1),
    ('Sucursal Piantini',   'Av. Winston Churchill #102, Piantini, Santo Domingo', 1),
    ('Sucursal Bella Vista','Av. Abraham Lincoln #210, Bella Vista, Santo Domingo', 1);
GO

-- ─────────────────────────────────────────────────────────────────
-- Roles
-- ─────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM dbo.Roles WHERE Nombre = 'Administrador')
    INSERT INTO dbo.Roles (Nombre) VALUES
    ('Administrador'), ('Gerente'), ('Cajero'), ('Mesero'), ('Cocinero');
GO

-- ─────────────────────────────────────────────────────────────────
-- Clientes
-- ─────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM dbo.Clientes WHERE Email = 'juan.perez@example.com')
    INSERT INTO dbo.Clientes (NombreCompleto, Email, Telefono, PasswordHash, Activo) VALUES
    ('Juan Perez Mateo',       'juan.perez@example.com',     '809-555-0101', '$2b$12$abcdefghijklmnopqrstuv', 1),
    ('Maria Rodriguez Gomez',  'maria.rodriguez@example.com','809-555-0102', '$2b$12$abcdefghijklmnopqrstuv', 1),
    ('Carlos Santana Diaz',    'carlos.santana@example.com', '829-555-0103', '$2b$12$abcdefghijklmnopqrstuv', 1),
    ('Ana Gonzalez Ureña',     'ana.gonzalez@example.com',   '849-555-0104', '$2b$12$abcdefghijklmnopqrstuv', 1);
GO

-- ─────────────────────────────────────────────────────────────────
-- Impuestos
-- ─────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM dbo.Impuestos WHERE Nombre = 'ITBIS')
    INSERT INTO dbo.Impuestos (Nombre, TasaPorcentaje, Activo) VALUES
    ('ITBIS',  18.00, 1),
    ('Exento',  0.00, 1);
GO

-- ─────────────────────────────────────────────────────────────────
-- Categorias
-- ─────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM dbo.Categorias WHERE Nombre = 'Entrantes')
    INSERT INTO dbo.Categorias (Nombre, Descripcion, Activo) VALUES
    ('Entrantes',          'Aperitivos y entradas',          1),
    ('Platos Fuertes',     'Platos principales',             1),
    ('Bebidas',            'Bebidas frias y calientes',      1),
    ('Postres',            'Postres y dulces',               1),
    ('Bebidas Alcoholicas','Cervezas, vinos y cocteles',     1);
GO

-- ─────────────────────────────────────────────────────────────────
-- Mesas
-- ─────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM dbo.Mesas WHERE Numero = 1)
    INSERT INTO dbo.Mesas (Numero, Descripcion, Capacidad, Activo, QrToken) VALUES
    (1, 'Mesa junto a la ventana', 4, 1, 'qr-token-mesa-001'),
    (2, 'Mesa central',            4, 1, 'qr-token-mesa-002'),
    (3, 'Mesa terraza',            6, 1, 'qr-token-mesa-003'),
    (4, 'Mesa privada',            8, 1, 'qr-token-mesa-004'),
    (5, 'Mesa barra',              2, 1, 'qr-token-mesa-005');
GO

-- ─────────────────────────────────────────────────────────────────
-- Core_Logs
-- ─────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM dbo.Core_Logs)
    INSERT INTO dbo.Core_Logs (Nivel, Origen, Mensaje, Data_JSON) VALUES
    ('INFO', 'Seed_Script', 'Base de datos inicializada con datos de prueba', NULL),
    ('INFO', 'Sync_CAJA',   'Sincronización inicial completada correctamente', NULL);
GO

-- ─────────────────────────────────────────────────────────────────
-- Password_Reset_Tokens
-- ─────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM dbo.Password_Reset_Tokens WHERE TokenHash = 'a1b2c3d4e5f6token001')
    INSERT INTO dbo.Password_Reset_Tokens (TokenHash, EntidadTipo, EntidadId, ExpiraEn, Usado) VALUES
    ('a1b2c3d4e5f6token001', 'CLIENTE',   1, DATEADD(HOUR, 1, GETDATE()), 0),
    ('a1b2c3d4e5f6token002', 'EMPLEADO',  1, DATEADD(HOUR, 1, GETDATE()), 0);
GO

-- ─────────────────────────────────────────────────────────────────
-- Categorias_Ingredientes
-- ─────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM dbo.Categorias_Ingredientes WHERE Nombre = 'Licores')
    INSERT INTO dbo.Categorias_Ingredientes (Nombre, Descripcion, Activo) VALUES
    ('Licores',   'Destilados y licores base',           1),
    ('Mixers',    'Jugos, refrescos y mezcladores',      1),
    ('Garnishes', 'Decoraciones y guarniciones',         1),
    ('Proteinas', 'Carnes, mariscos y proteinas',        1),
    ('Lacteos',   'Quesos, cremas y lacteos',            1);
GO

-- ─────────────────────────────────────────────────────────────────
-- Empleados
-- ─────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM dbo.Empleados WHERE Email = 'pedro.martinez@coredb.com')
    INSERT INTO dbo.Empleados (RolId, SucursalId, DocumentoIdentidad, NombreCompleto, Email, PasswordHash, Activo) VALUES
    (1, 1, '00112345671', 'Pedro Martinez Reyes',     'pedro.martinez@coredb.com', '$2b$12$abcdefghijklmnopqrstuv', 1),
    (2, 1, '00112345672', 'Luisa Fernandez Castillo', 'luisa.fernandez@coredb.com','$2b$12$abcdefghijklmnopqrstuv', 1),
    (3, 1, '00112345673', 'Miguel Angel Soto',        'miguel.soto@coredb.com',    '$2b$12$abcdefghijklmnopqrstuv', 1),
    (4, 2, '00112345674', 'Carla Beatriz Nuñez',      'carla.nunez@coredb.com',    '$2b$12$abcdefghijklmnopqrstuv', 1),
    (5, 2, '00112345675', 'Roberto Carlos Vargas',    'roberto.vargas@coredb.com', '$2b$12$abcdefghijklmnopqrstuv', 1);
GO

-- ─────────────────────────────────────────────────────────────────
-- Productos
-- ─────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM dbo.Productos WHERE SKU = 'ENT-001')
    INSERT INTO dbo.Productos (CategoriaId, ImpuestoId, SKU, Nombre, Descripcion, PrecioBase, CostoPromedio, TipoControlInventario, Activo, ImagenURL) VALUES
    (1, 1, 'ENT-001', 'Tequeños de Queso',    'Porción de 8 unidades con salsa de la casa',    320.00, 120.00, 'PRODUCTO',     1, NULL),
    (1, 1, 'ENT-002', 'Alitas BBQ',           'Porción de 10 alitas en salsa BBQ',             450.00, 180.00, 'PRODUCTO',     1, NULL),
    (2, 1, 'PLA-001', 'Mofongo con Camarones','Mofongo relleno de camarones al ajillo',        680.00, 280.00, 'PRODUCTO',     1, NULL),
    (2, 1, 'PLA-002', 'Pollo Guisado',        'Pollo guisado con arroz blanco y habichuelas',  520.00, 200.00, 'PRODUCTO',     1, NULL),
    (3, 1, 'BEB-001', 'Refresco',             'Refresco 12oz, varios sabores',                  90.00,  25.00, 'PRODUCTO',     1, NULL),
    (3, 2, 'BEB-002', 'Agua Mineral',         'Botella de agua 500ml',                          60.00,  15.00, 'PRODUCTO',     1, NULL),
    (4, 1, 'POS-001', 'Tres Leches',          'Porción de pastel tres leches',                 220.00,  80.00, 'PRODUCTO',     1, NULL),
    (5, 1, 'ALC-001', 'Cerveza Presidente',   'Cerveza nacional 12oz',                         150.00,  60.00, 'PRODUCTO',     1, NULL),
    (5, 1, 'ALC-002', 'Mojito Clasico',       'Coctel de ron, menta y limón',                  280.00,  90.00, 'INGREDIENTES', 1, NULL);
GO

-- ─────────────────────────────────────────────────────────────────
-- Ingredientes
-- ─────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM dbo.Ingredientes WHERE Nombre = 'Ron Blanco')
    INSERT INTO dbo.Ingredientes (CategoriaId, Nombre, UnidadMedida, CantidadActual, CantidadMinima, CantidadReorden, CostoUnitario, Activo) VALUES
    (1, 'Ron Blanco',     'ml', 5000.0000, 500.0000, 1000.0000, 0.4500, 1),
    (2, 'Jugo de Limón',  'ml', 3000.0000, 300.0000,  600.0000, 0.0300, 1),
    (3, 'Hojas de Menta', 'g',   500.0000,  50.0000,  100.0000, 0.0800, 1),
    (2, 'Agua con Gas',   'ml', 8000.0000, 500.0000, 1000.0000, 0.0100, 1),
    (2, 'Azúcar',         'g',  2000.0000, 200.0000,  500.0000, 0.0050, 1);
GO

-- ─────────────────────────────────────────────────────────────────
-- Secuencias_NCF
-- ─────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM dbo.Secuencias_NCF WHERE TipoNcf = 'B01' AND SucursalId = 1)
    INSERT INTO dbo.Secuencias_NCF (TipoNcf, Serie, RangoDesde, RangoHasta, SecuenciaActual, FechaVencimiento, Activo, SucursalId) VALUES
    ('B01', 'B01', 1, 50000, 1, DATEADD(YEAR, 1, GETDATE()), 1, 1),
    ('B02', 'B02', 1, 50000, 1, DATEADD(YEAR, 1, GETDATE()), 1, 1),
    ('B01', 'B01', 1, 50000, 1, DATEADD(YEAR, 1, GETDATE()), 1, 2);
GO

-- ─────────────────────────────────────────────────────────────────
-- Promociones
-- Se agregan 'Descuento Estudiantes' (ELEGIBILIDAD) y 'Cupon Bienvenida10'
-- (CODIGO_PROMO) para poder alimentar Promociones_Elegibilidad y
-- Codigos_Promocionales, que antes no tenían ningún dato de prueba.
-- ─────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM dbo.Promociones WHERE Nombre = 'Happy Hour Bebidas')
    INSERT INTO dbo.Promociones (Nombre, Descripcion, TipoDescuento, Valor, FechaInicio, FechaFin, Activo, Prioridad, AplicaA, TipoAplicacion, AplicaHappyHour, HoraInicioHH, HoraFinHH, PrecioMinimoFinal) VALUES
    ('Happy Hour Bebidas',    '20% de descuento en bebidas alcoholicas',                       'PORCENTAJE', 20.00, GETDATE(), DATEADD(MONTH, 3, GETDATE()), 1, 1, 'CATEGORIAS', 'AUTOMATICA',   1, '17:00', '19:00', NULL),
    ('Descuento Apertura',    'RD$100 de descuento en platos fuertes',                         'MONTO_FIJO', 100.00, GETDATE(), DATEADD(MONTH, 1, GETDATE()), 1, 2, 'CATEGORIAS', 'AUTOMATICA',   0, NULL,    NULL,    NULL),
    ('Promo General 10%',     '10% de descuento en toda la cuenta',                            'PORCENTAJE', 10.00, GETDATE(), NULL,                          1, 0, 'TODOS',      'AUTOMATICA',   0, NULL,    NULL,    NULL),
    ('Descuento Estudiantes', '15% de descuento presentando carnet estudiantil',               'PORCENTAJE', 15.00, GETDATE(), NULL,                          1, 3, 'TODOS',      'ELEGIBILIDAD', 0, NULL,    NULL,    NULL),
    ('Cupon Bienvenida10',    '10% de descuento con código promocional de bienvenida',         'PORCENTAJE', 10.00, GETDATE(), DATEADD(MONTH, 6, GETDATE()), 1, 4, 'TODOS',      'CODIGO_PROMO', 0, NULL,    NULL,    200.00);
GO

-- ─────────────────────────────────────────────────────────────────
-- Inventario_Actual (solo productos PRODUCTO)
-- ─────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM dbo.Inventario_Actual WHERE ProductoId = 1)
    INSERT INTO dbo.Inventario_Actual (ProductoId, CantidadDisponible, StockMinimo) VALUES
    (1,  50, 10), (2,  40, 10), (3, 30, 5), (4, 35, 5),
    (5, 200, 30), (6, 150, 20), (7, 25, 5), (8, 120, 24);
GO

-- ─────────────────────────────────────────────────────────────────
-- Movimientos_Inventario
-- ─────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM dbo.Movimientos_Inventario)
    INSERT INTO dbo.Movimientos_Inventario (ProductoId, EmpleadoId, TipoMovimiento, Cantidad, Motivo, movimiento_local_uuid, Factura_Local_UUID) VALUES
    (1, 1, 'ENTRADA',  60, 'Compra a proveedor', NEWID(), NULL),
    (1, 3, 'SALIDA',  -10, 'Venta en sucursal',  NEWID(), NEWID()),
    (5, 1, 'ENTRADA', 240, 'Compra a proveedor', NEWID(), NULL),
    (8, 2, 'AJUSTE',   -5, 'Producto dañado',    NEWID(), NULL);
GO

-- ─────────────────────────────────────────────────────────────────
-- Pedidos_Global
-- ─────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM dbo.Pedidos_Global)
    INSERT INTO dbo.Pedidos_Global (ClienteId, EmpleadoId, Mesa, CanalOrigen, Estado, Subtotal, TotalImpuestos, PropinaLegal, TotalGeneral, Factura_Local_UUID, PropinaExtra) VALUES
    (1, 4, '1', 'SALON',     'PAGADO',          1100.00, 198.00, 110.00, 1408.00, NEWID(), 50.00),
    (2, 4, '2', 'SALON',     'PAGADO',           680.00, 122.40,  68.00,  870.40, NEWID(),  0.00),
    (3, NULL, NULL, 'APP_MOVIL', 'PENDIENTE',    540.00,  97.20,   0.00,  637.20, NULL,     0.00),
    (NULL, 5, '3', 'SALON',  'EN_PREPARACION',   320.00,  57.60,  32.00,  409.60, NULL,     0.00);
GO

-- ─────────────────────────────────────────────────────────────────
-- Aplicaciones_Promocion (ledger sincronizado desde CAJA)
-- Antes sin datos de prueba: se agregan 2 registros de ejemplo,
-- uno para una promoción AUTOMATICA y otro para una CODIGO_PROMO.
-- ─────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM dbo.Aplicaciones_Promocion)
BEGIN
    INSERT INTO dbo.Aplicaciones_Promocion
        (PromocionId, NombrePromocionSnap, TipoAplicacion, PedidoId, FacturaUUID, EmpleadoId, EmpleadoAutorizadorId, ClienteId, IdentificadorCapturado, MontoDescuento, Terminal, Notas)
    SELECT p.Id, p.Nombre, p.TipoAplicacion, pg.Id, pg.Factura_Local_UUID, pg.EmpleadoId, NULL, pg.ClienteId, NULL, 110.00, 'CAJA-01', 'Aplicado automáticamente en pedido de salón'
    FROM dbo.Promociones p
    CROSS JOIN dbo.Pedidos_Global pg
    WHERE p.Nombre = 'Promo General 10%' AND pg.Mesa = '1'

    UNION ALL

    SELECT p.Id, p.Nombre, p.TipoAplicacion, pg.Id, pg.Factura_Local_UUID, pg.EmpleadoId,
           (SELECT Id FROM dbo.Empleados WHERE Email = 'luisa.fernandez@coredb.com'),
           pg.ClienteId, 'BIENVENIDA10', 68.00, 'CAJA-02', 'Código promocional validado por supervisor'
    FROM dbo.Promociones p
    CROSS JOIN dbo.Pedidos_Global pg
    WHERE p.Nombre = 'Cupon Bienvenida10' AND pg.Mesa = '2';
END
GO

-- ─────────────────────────────────────────────────────────────────
-- SupervisorSessionAudit
-- Antes sin datos de prueba: se agregan 2 sesiones de ejemplo.
-- ─────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM dbo.SupervisorSessionAudit)
    INSERT INTO dbo.SupervisorSessionAudit (supervisor_id, cajero_id, terminal, inicio, fin, motivo_fin)
    SELECT
        (SELECT Id FROM dbo.Empleados WHERE Email = 'luisa.fernandez@coredb.com'),
        (SELECT Id FROM dbo.Empleados WHERE Email = 'miguel.soto@coredb.com'),
        'CAJA-01', DATEADD(HOUR, -3, GETDATE()), DATEADD(HOUR, -2, GETDATE()), 'AUTORIZACION_DESCUENTO'
    UNION ALL
    SELECT
        (SELECT Id FROM dbo.Empleados WHERE Email = 'pedro.martinez@coredb.com'),
        (SELECT Id FROM dbo.Empleados WHERE Email = 'miguel.soto@coredb.com'),
        'CAJA-02', DATEADD(HOUR, -1, GETDATE()), DATEADD(MINUTE, -45, GETDATE()), 'CIERRE_TURNO';
GO

-- ─────────────────────────────────────────────────────────────────
-- Promociones_Productos
-- ─────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM dbo.Promociones_Productos)
    INSERT INTO dbo.Promociones_Productos (PromocionId, ProductoId) VALUES
    (2, 3), (2, 4);
GO

-- ─────────────────────────────────────────────────────────────────
-- Promociones_Categorias
-- ─────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM dbo.Promociones_Categorias)
    INSERT INTO dbo.Promociones_Categorias (PromocionId, CategoriaId) VALUES
    (1, 5), (2, 2);
GO

-- ─────────────────────────────────────────────────────────────────
-- Codigos_Promocionales
-- Antes sin datos de prueba: código asociado a 'Cupon Bienvenida10'.
-- ─────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM dbo.Codigos_Promocionales WHERE Codigo = 'BIENVENIDA10')
    INSERT INTO dbo.Codigos_Promocionales (PromocionId, Codigo, FechaInicio, FechaFin, UsoMaximo, UnUsoPorCliente, MontoMinimoCompra, Activo)
    SELECT Id, 'BIENVENIDA10', GETDATE(), DATEADD(MONTH, 6, GETDATE()), 500, 1, 300.00, 1
    FROM dbo.Promociones WHERE Nombre = 'Cupon Bienvenida10';
GO

-- ─────────────────────────────────────────────────────────────────
-- Promociones_Elegibilidad
-- Antes sin datos de prueba: regla asociada a 'Descuento Estudiantes'.
-- ─────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM dbo.Promociones_Elegibilidad)
    INSERT INTO dbo.Promociones_Elegibilidad (PromocionId, EtiquetaIdentificador, RequiereIdentificador)
    SELECT Id, 'Carnet Estudiantil', 1
    FROM dbo.Promociones WHERE Nombre = 'Descuento Estudiantes';
GO

-- ─────────────────────────────────────────────────────────────────
-- Recetas_Producto (Mojito Clasico)
-- ─────────────────────────────────────────────────────────────────
IF NOT EXISTS (
    SELECT 1 FROM dbo.Recetas_Producto rp
    INNER JOIN dbo.Productos p ON p.Id = rp.ProductoId
    WHERE p.SKU = 'ALC-002'
)
    INSERT INTO dbo.Recetas_Producto (ProductoId, Descripcion, Activo)
    SELECT Id, 'Receta estándar para Mojito Clásico (1 vaso)', 1
    FROM dbo.Productos WHERE SKU = 'ALC-002';
GO

-- ─────────────────────────────────────────────────────────────────
-- Componentes_Receta (Mojito)
-- ─────────────────────────────────────────────────────────────────
DECLARE @recetaId INT;
SELECT @recetaId = rp.Id
FROM dbo.Recetas_Producto rp
INNER JOIN dbo.Productos p ON p.Id = rp.ProductoId
WHERE p.SKU = 'ALC-002';

IF @recetaId IS NOT NULL AND NOT EXISTS (SELECT 1 FROM dbo.Componentes_Receta WHERE RecetaId = @recetaId)
    INSERT INTO dbo.Componentes_Receta (RecetaId, IngredienteId, CantidadRequerida, UnidadMedida)
    SELECT @recetaId, i.Id, src.CantidadReq, src.Unidad
    FROM (VALUES
        ('Ron Blanco',    60.0000, 'ml'),
        ('Jugo de Limón', 30.0000, 'ml'),
        ('Hojas de Menta',10.0000, 'g'),
        ('Agua con Gas',  90.0000, 'ml'),
        ('Azúcar',        15.0000, 'g')
    ) AS src(NombreIng, CantidadReq, Unidad)
    INNER JOIN dbo.Ingredientes i ON i.Nombre = src.NombreIng;
GO

-- ─────────────────────────────────────────────────────────────────
-- Detalles_Pedido
-- ─────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM dbo.Detalles_Pedido)
    INSERT INTO dbo.Detalles_Pedido (PedidoId, ProductoId, Cantidad, PrecioUnitarioHistorico, ImpuestoHistorico, MontoImpuesto, SubtotalLinea, Detalle_Local_UUID) VALUES
    (1, 3, 1, 680.00, 18.00, 122.40, 680.00, NEWID()),
    (1, 7, 1, 220.00, 18.00,  39.60, 220.00, NEWID()),
    (1, 1, 1, 320.00, 18.00,  57.60, 320.00, NEWID()),
    (2, 3, 1, 680.00, 18.00, 122.40, 680.00, NEWID()),
    (3, 4, 1, 520.00, 18.00,  93.60, 520.00, NEWID()),
    (4, 1, 1, 320.00, 18.00,  57.60, 320.00, NEWID());
GO

-- ─────────────────────────────────────────────────────────────────
-- Historial_NCF
-- ─────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM dbo.Historial_NCF)
    INSERT INTO dbo.Historial_NCF (SecuenciaId, NcfAsignado, PedidoId, EmpleadoId) VALUES
    (1, 'B0100000001', 1, 4),
    (1, 'B0100000002', 2, 4);
GO

-- ─────────────────────────────────────────────────────────────────
-- Division_Cuenta
-- ─────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM dbo.Division_Cuenta)
    INSERT INTO dbo.Division_Cuenta (PedidoId, NumeroPartes, MontoPorParte, MontosPersonalizadosJson, EmpleadoId) VALUES
    (1, 2, 704.00, NULL, 4),
    (2, 1, 870.40, '[{"parte":1,"monto":870.40}]', 4);
GO

-- ─────────────────────────────────────────────────────────────────
-- Movimientos_Ingrediente
-- ─────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM dbo.Movimientos_Ingrediente)
    INSERT INTO dbo.Movimientos_Ingrediente (IngredienteId, EmpleadoId, TipoMovimiento, Cantidad, CantidadAnterior, CantidadNueva, DocumentoReferencia, Notas) VALUES
    (1, 1, 'CARGA_INICIAL', 5000.0000, 0.0000, 5000.0000, 'CARGA-001', 'Carga inicial de Ron Blanco'),
    (2, 1, 'CARGA_INICIAL', 3000.0000, 0.0000, 3000.0000, 'CARGA-001', 'Carga inicial de Jugo de Limón'),
    (3, 1, 'CARGA_INICIAL',  500.0000, 0.0000,  500.0000, 'CARGA-001', 'Carga inicial de Hojas de Menta'),
    (4, 1, 'CARGA_INICIAL', 8000.0000, 0.0000, 8000.0000, 'CARGA-001', 'Carga inicial de Agua con Gas'),
    (5, 1, 'CARGA_INICIAL', 2000.0000, 0.0000, 2000.0000, 'CARGA-001', 'Carga inicial de Azúcar');
GO

-- ─────────────────────────────────────────────────────────────────
-- Modificadores_Item
-- ─────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM dbo.Modificadores_Item)
    INSERT INTO dbo.Modificadores_Item (DetallePedidoUuid, Descripcion) VALUES
    (NEWID(), 'Sin picante'),
    (NEWID(), 'Extra salsa rosada'),
    (NEWID(), 'Bien cocido'),
    (NEWID(), 'Sin cebolla');
GO

PRINT '✔ Seed de datos de prueba completado (v3 — incluye promociones extendido y auditoría).';
GO