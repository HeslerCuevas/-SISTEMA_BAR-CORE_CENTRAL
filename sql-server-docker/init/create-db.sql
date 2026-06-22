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
        CostoPromedio NUMERIC(12,2) NULL DEFAULT 0,
        EsInventariable BIT NOT NULL DEFAULT 1,
        Activo BIT NOT NULL DEFAULT 1,
        Ultima_Modificacion DATETIME NULL DEFAULT GETDATE(),
        ImagenURL NVARCHAR(1000) NULL,
        CONSTRAINT FK_Productos_Categorias FOREIGN KEY (CategoriaId) REFERENCES Categorias(Id),
        CONSTRAINT FK_Productos_Impuestos FOREIGN KEY (ImpuestoId) REFERENCES Impuestos(Id)
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
        AplicaHappyHour BIT NOT NULL DEFAULT 0,
        HoraInicioHH NVARCHAR(5) NULL,
        HoraFinHH NVARCHAR(5) NULL,
        FechaCreacion DATETIME NOT NULL DEFAULT GETDATE()
    );
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

-- ─────────────────────────────────────────────────────────────────
-- TABLAS CON DEPENDENCIA DE NIVEL 4
-- ─────────────────────────────────────────────────────────────────

IF OBJECT_ID('dbo.Modificadores_Item', 'U') IS NULL
BEGIN
    CREATE TABLE Modificadores_Item (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        DetallePedidoId INT NOT NULL,
        Descripcion NVARCHAR(255) NOT NULL,
        FechaRegistro DATETIME NULL DEFAULT GETDATE(),
        CONSTRAINT FK_ModificadoresItem_DetallesPedido FOREIGN KEY (DetallePedidoId) REFERENCES Detalles_Pedido(Id)
    );

    CREATE INDEX IX_Modificadores_Item_DetallePedidoId ON Modificadores_Item(DetallePedidoId);
END
GO

PRINT 'Base de datos Core_Master_DB y todas las tablas creadas correctamente.';
GO





-- ═════════════════════════════════════════════════════════════════
-- INSERCIÓN DE DATOS DE PRUEBA
-- ═════════════════════════════════════════════════════════════════

USE Core_Master_DB;
GO

-- ─────────────────────────────────────────────────────────────────
-- Sucursales
-- ─────────────────────────────────────────────────────────────────
INSERT INTO Sucursales (Nombre, Direccion, Activo) VALUES
('Sucursal Naco', 'Av. Tiradentes #45, Naco, Santo Domingo', 1),
('Sucursal Piantini', 'Av. Winston Churchill #102, Piantini, Santo Domingo', 1),
('Sucursal Bella Vista', 'Av. Abraham Lincoln #210, Bella Vista, Santo Domingo', 1);
GO

-- ─────────────────────────────────────────────────────────────────
-- Roles
-- ─────────────────────────────────────────────────────────────────
INSERT INTO Roles (Nombre) VALUES
('Administrador'),
('Gerente'),
('Cajero'),
('Mesero'),
('Cocinero');
GO

-- ─────────────────────────────────────────────────────────────────
-- Clientes
-- ─────────────────────────────────────────────────────────────────
INSERT INTO Clientes (NombreCompleto, Email, Telefono, PasswordHash, Activo) VALUES
('Juan Perez Mateo', 'juan.perez@example.com', '809-555-0101', '$2b$12$abcdefghijklmnopqrstuv', 1),
('Maria Rodriguez Gomez', 'maria.rodriguez@example.com', '809-555-0102', '$2b$12$abcdefghijklmnopqrstuv', 1),
('Carlos Santana Diaz', 'carlos.santana@example.com', '829-555-0103', '$2b$12$abcdefghijklmnopqrstuv', 1),
('Ana Gonzalez Ureña', 'ana.gonzalez@example.com', '849-555-0104', '$2b$12$abcdefghijklmnopqrstuv', 1);
GO

-- ─────────────────────────────────────────────────────────────────
-- Impuestos
-- ─────────────────────────────────────────────────────────────────
INSERT INTO Impuestos (Nombre, TasaPorcentaje, Activo) VALUES
('ITBIS', 18.00, 1),
('Exento', 0.00, 1);
GO

-- ─────────────────────────────────────────────────────────────────
-- Categorias
-- ─────────────────────────────────────────────────────────────────
INSERT INTO Categorias (Nombre, Descripcion, Activo) VALUES
('Entrantes', 'Aperitivos y entradas', 1),
('Platos Fuertes', 'Platos principales', 1),
('Bebidas', 'Bebidas frias y calientes', 1),
('Postres', 'Postres y dulces', 1),
('Bebidas Alcoholicas', 'Cervezas, vinos y cocteles', 1);
GO

-- ─────────────────────────────────────────────────────────────────
-- Mesas
-- ─────────────────────────────────────────────────────────────────
INSERT INTO Mesas (Numero, Descripcion, Capacidad, Activo, QrToken) VALUES
(1, 'Mesa junto a la ventana', 4, 1, 'qr-token-mesa-001'),
(2, 'Mesa central', 4, 1, 'qr-token-mesa-002'),
(3, 'Mesa terraza', 6, 1, 'qr-token-mesa-003'),
(4, 'Mesa privada', 8, 1, 'qr-token-mesa-004'),
(5, 'Mesa barra', 2, 1, 'qr-token-mesa-005');
GO

-- ─────────────────────────────────────────────────────────────────
-- Password_Reset_Tokens
-- ─────────────────────────────────────────────────────────────────
INSERT INTO Password_Reset_Tokens (TokenHash, EntidadTipo, EntidadId, ExpiraEn, Usado) VALUES
('a1b2c3d4e5f6token001', 'CLIENTE', 1, DATEADD(HOUR, 1, GETDATE()), 0),
('a1b2c3d4e5f6token002', 'EMPLEADO', 1, DATEADD(HOUR, 1, GETDATE()), 0);
GO

-- ─────────────────────────────────────────────────────────────────
-- Empleados
-- ─────────────────────────────────────────────────────────────────
INSERT INTO Empleados (RolId, SucursalId, DocumentoIdentidad, NombreCompleto, Email, PasswordHash, Activo) VALUES
(1, 1, '00112345671', 'Pedro Martinez Reyes', 'pedro.martinez@coredb.com', '$2b$12$abcdefghijklmnopqrstuv', 1),
(2, 1, '00112345672', 'Luisa Fernandez Castillo', 'luisa.fernandez@coredb.com', '$2b$12$abcdefghijklmnopqrstuv', 1),
(3, 1, '00112345673', 'Miguel Angel Soto', 'miguel.soto@coredb.com', '$2b$12$abcdefghijklmnopqrstuv', 1),
(4, 2, '00112345674', 'Carla Beatriz Nuñez', 'carla.nunez@coredb.com', '$2b$12$abcdefghijklmnopqrstuv', 1),
(5, 2, '00112345675', 'Roberto Carlos Vargas', 'roberto.vargas@coredb.com', '$2b$12$abcdefghijklmnopqrstuv', 1);
GO

-- ─────────────────────────────────────────────────────────────────
-- Productos
-- ─────────────────────────────────────────────────────────────────
INSERT INTO Productos (CategoriaId, ImpuestoId, SKU, Nombre, Descripcion, PrecioBase, CostoPromedio, EsInventariable, Activo, ImagenURL) VALUES
(1, 1, 'ENT-001', 'Tequeños de Queso', 'Porción de 8 unidades con salsa de la casa', 320.00, 120.00, 1, 1, NULL),
(1, 1, 'ENT-002', 'Alitas BBQ', 'Porción de 10 alitas en salsa BBQ', 450.00, 180.00, 1, 1, NULL),
(2, 1, 'PLA-001', 'Mofongo con Camarones', 'Mofongo relleno de camarones al ajillo', 680.00, 280.00, 1, 1, NULL),
(2, 1, 'PLA-002', 'Pollo Guisado', 'Pollo guisado con arroz blanco y habichuelas', 520.00, 200.00, 1, 1, NULL),
(3, 1, 'BEB-001', 'Refresco', 'Refresco 12oz, varios sabores', 90.00, 25.00, 1, 1, NULL),
(3, 2, 'BEB-002', 'Agua Mineral', 'Botella de agua 500ml', 60.00, 15.00, 1, 1, NULL),
(4, 1, 'POS-001', 'Tres Leches', 'Porción de pastel tres leches', 220.00, 80.00, 1, 1, NULL),
(5, 1, 'ALC-001', 'Cerveza Presidente', 'Cerveza nacional 12oz', 150.00, 60.00, 1, 1, NULL);
GO

-- ─────────────────────────────────────────────────────────────────
-- Secuencias_NCF
-- ─────────────────────────────────────────────────────────────────
INSERT INTO Secuencias_NCF (TipoNcf, Serie, RangoDesde, RangoHasta, SecuenciaActual, FechaVencimiento, Activo, SucursalId) VALUES
('B01', 'B01', 1, 50000, 1, DATEADD(YEAR, 1, GETDATE()), 1, 1),
('B02', 'B02', 1, 50000, 1, DATEADD(YEAR, 1, GETDATE()), 1, 1),
('B01', 'B01', 1, 50000, 1, DATEADD(YEAR, 1, GETDATE()), 1, 2);
GO

-- ─────────────────────────────────────────────────────────────────
-- Promociones
-- ─────────────────────────────────────────────────────────────────
INSERT INTO Promociones (Nombre, Descripcion, TipoDescuento, Valor, FechaInicio, FechaFin, Activo, Prioridad, AplicaA, AplicaHappyHour, HoraInicioHH, HoraFinHH) VALUES
('Happy Hour Bebidas', '20% de descuento en bebidas alcoholicas', 'PORCENTAJE', 20.00, GETDATE(), DATEADD(MONTH, 3, GETDATE()), 1, 1, 'CATEGORIAS', 1, '17:00', '19:00'),
('Descuento Apertura', 'RD$100 de descuento en platos fuertes', 'MONTO_FIJO', 100.00, GETDATE(), DATEADD(MONTH, 1, GETDATE()), 1, 2, 'CATEGORIAS', 0, NULL, NULL),
('Promo General 10%', '10% de descuento en toda la cuenta', 'PORCENTAJE', 10.00, GETDATE(), NULL, 1, 0, 'TODOS', 0, NULL, NULL);
GO

-- ─────────────────────────────────────────────────────────────────
-- Inventario_Actual
-- ─────────────────────────────────────────────────────────────────
INSERT INTO Inventario_Actual (ProductoId, CantidadDisponible, StockMinimo) VALUES
(1, 50, 10),
(2, 40, 10),
(3, 30, 5),
(4, 35, 5),
(5, 200, 30),
(6, 150, 20),
(7, 25, 5),
(8, 120, 24);
GO

-- ─────────────────────────────────────────────────────────────────
-- Movimientos_Inventario
-- ─────────────────────────────────────────────────────────────────
INSERT INTO Movimientos_Inventario (ProductoId, EmpleadoId, TipoMovimiento, Cantidad, Motivo, movimiento_local_uuid, Factura_Local_UUID) VALUES
(1, 1, 'ENTRADA', 60, 'Compra a proveedor', NEWID(), NULL),
(1, 3, 'SALIDA', 10, 'Venta en sucursal', NEWID(), NEWID()),
(5, 1, 'ENTRADA', 240, 'Compra a proveedor', NEWID(), NULL),
(8, 2, 'AJUSTE', -5, 'Producto dañado', NEWID(), NULL);
GO

-- ─────────────────────────────────────────────────────────────────
-- Pedidos_Global
-- ─────────────────────────────────────────────────────────────────
INSERT INTO Pedidos_Global (ClienteId, EmpleadoId, Mesa, CanalOrigen, Estado, Subtotal, TotalImpuestos, PropinaLegal, TotalGeneral, Factura_Local_UUID, PropinaExtra) VALUES
(1, 4, '1', 'SALON', 'PAGADO', 1100.00, 198.00, 110.00, 1408.00, NEWID(), 50.00),
(2, 4, '2', 'SALON', 'PAGADO', 680.00, 122.40, 68.00, 870.40, NEWID(), 0.00),
(3, NULL, NULL, 'APP_MOVIL', 'PENDIENTE', 540.00, 97.20, 0.00, 637.20, NULL, 0.00),
(NULL, 5, '3', 'SALON', 'EN_PREPARACION', 320.00, 57.60, 32.00, 409.60, NULL, 0.00);
GO

-- ─────────────────────────────────────────────────────────────────
-- Promociones_Productos
-- ─────────────────────────────────────────────────────────────────
INSERT INTO Promociones_Productos (PromocionId, ProductoId) VALUES
(2, 3),
(2, 4);
GO

-- ─────────────────────────────────────────────────────────────────
-- Promociones_Categorias
-- ─────────────────────────────────────────────────────────────────
INSERT INTO Promociones_Categorias (PromocionId, CategoriaId) VALUES
(1, 5),
(2, 2);
GO

-- ─────────────────────────────────────────────────────────────────
-- Detalles_Pedido
-- ─────────────────────────────────────────────────────────────────
INSERT INTO Detalles_Pedido (PedidoId, ProductoId, Cantidad, PrecioUnitarioHistorico, ImpuestoHistorico, MontoImpuesto, SubtotalLinea, Detalle_Local_UUID) VALUES
(1, 3, 1, 680.00, 18.00, 122.40, 680.00, NEWID()),
(1, 7, 1, 220.00, 18.00, 39.60, 220.00, NEWID()),
(1, 1, 1, 320.00, 18.00, 57.60, 320.00, NEWID()),
(2, 3, 1, 680.00, 18.00, 122.40, 680.00, NEWID()),
(3, 4, 1, 520.00, 18.00, 93.60, 520.00, NEWID()),
(4, 1, 1, 320.00, 18.00, 57.60, 320.00, NEWID());
GO

-- ─────────────────────────────────────────────────────────────────
-- Historial_NCF
-- ─────────────────────────────────────────────────────────────────
INSERT INTO Historial_NCF (SecuenciaId, NcfAsignado, PedidoId, EmpleadoId) VALUES
(1, 'B0100000001', 1, 4),
(1, 'B0100000002', 2, 4);
GO

-- ─────────────────────────────────────────────────────────────────
-- Division_Cuenta
-- ─────────────────────────────────────────────────────────────────
INSERT INTO Division_Cuenta (PedidoId, NumeroPartes, MontoPorParte, MontosPersonalizadosJson, EmpleadoId) VALUES
(1, 2, 704.00, NULL, 4),
(2, 1, 870.40, '[{"parte":1,"monto":870.40}]', 4);
GO

-- ─────────────────────────────────────────────────────────────────
-- Modificadores_Item
-- ─────────────────────────────────────────────────────────────────
INSERT INTO Modificadores_Item (DetallePedidoId, Descripcion) VALUES
(1, 'Sin picante'),
(1, 'Extra salsa rosada'),
(3, 'Bien cocido'),
(5, 'Sin cebolla');
GO

PRINT 'Datos de prueba insertados correctamente.';
GO