-- ============================================================
-- MIGRATION V2: Ingredient-Based Inventory System
-- Database: Core_Master_DB
-- Run this script MANUALLY on SQL Server before restarting
-- the application. The application's create_all() will NOT
-- alter existing tables — this script handles that.
-- ============================================================

USE [Core_Master_DB];
GO

-- ============================================================
-- PART 1: ALTER EXISTING TABLE — Productos
-- Add TipoControlInventario column
-- Values: PRODUCTO | INGREDIENTES | NINGUNO
-- Default: PRODUCTO (safe default — preserves existing behavior)
-- ============================================================

IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'Productos'
      AND COLUMN_NAME = 'TipoControlInventario'
)
BEGIN
    ALTER TABLE [dbo].[Productos]
    ADD [TipoControlInventario] VARCHAR(20) NOT NULL CONSTRAINT [DF_Productos_TipoControlInventario] DEFAULT ('PRODUCTO');

    PRINT 'Column TipoControlInventario added to Productos.';
END
ELSE
    PRINT 'Column TipoControlInventario already exists in Productos. Skipped.';
GO

-- Backfill: products with EsInventariable = 0 get NINGUNO
UPDATE [dbo].[Productos]
SET [TipoControlInventario] = 'NINGUNO'
WHERE [EsInventariable] = 0
  AND [TipoControlInventario] = 'PRODUCTO';
GO

-- Add CHECK constraint for TipoControlInventario
IF NOT EXISTS (
    SELECT 1 FROM sys.check_constraints
    WHERE name = 'CK_Productos_TipoControlInventario'
)
BEGIN
    ALTER TABLE [dbo].[Productos]
    ADD CONSTRAINT [CK_Productos_TipoControlInventario]
    CHECK ([TipoControlInventario] IN ('PRODUCTO', 'INGREDIENTES', 'NINGUNO'));

    PRINT 'CHECK constraint CK_Productos_TipoControlInventario added.';
END
ELSE
    PRINT 'CHECK constraint CK_Productos_TipoControlInventario already exists. Skipped.';
GO

-- ============================================================
-- PART 2: NEW TABLE — Categorias_Ingredientes
-- ============================================================

IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_NAME = 'Categorias_Ingredientes'
)
BEGIN
    CREATE TABLE [dbo].[Categorias_Ingredientes] (
        [Id]                  INT IDENTITY(1,1)  NOT NULL,
        [Nombre]              VARCHAR(100)        NOT NULL,
        [Descripcion]         NVARCHAR(500)       NULL,
        [Activo]              BIT                 NOT NULL CONSTRAINT [DF_CatIng_Activo] DEFAULT (1),
        [Ultima_Modificacion] DATETIME            NOT NULL CONSTRAINT [DF_CatIng_UltimaModif] DEFAULT GETDATE(),
        CONSTRAINT [PK_Categorias_Ingredientes] PRIMARY KEY ([Id]),
        CONSTRAINT [UQ_CatIng_Nombre] UNIQUE ([Nombre])
    );

    PRINT 'Table Categorias_Ingredientes created.';
END
ELSE
    PRINT 'Table Categorias_Ingredientes already exists. Skipped.';
GO

-- ============================================================
-- PART 3: NEW TABLE — Ingredientes
-- ============================================================

IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_NAME = 'Ingredientes'
)
BEGIN
    CREATE TABLE [dbo].[Ingredientes] (
        [Id]                  INT IDENTITY(1,1)  NOT NULL,
        [CategoriaId]         INT                NOT NULL,
        [Nombre]              VARCHAR(150)        NOT NULL,
        [Descripcion]         NVARCHAR(500)       NULL,
        [UnidadMedida]        VARCHAR(20)         NOT NULL,
        [CantidadActual]      NUMERIC(12, 4)      NOT NULL CONSTRAINT [DF_Ing_CantidadActual]  DEFAULT (0),
        [CantidadMinima]      NUMERIC(12, 4)      NOT NULL CONSTRAINT [DF_Ing_CantidadMinima]  DEFAULT (0),
        [CantidadReorden]     NUMERIC(12, 4)      NOT NULL CONSTRAINT [DF_Ing_CantidadReorden] DEFAULT (0),
        [CostoUnitario]       NUMERIC(12, 4)      NOT NULL CONSTRAINT [DF_Ing_CostoUnitario]   DEFAULT (0),
        [Activo]              BIT                 NOT NULL CONSTRAINT [DF_Ing_Activo]           DEFAULT (1),
        [Ultima_Modificacion] DATETIME            NOT NULL CONSTRAINT [DF_Ing_UltimaModif]     DEFAULT GETDATE(),
        CONSTRAINT [PK_Ingredientes] PRIMARY KEY ([Id]),
        CONSTRAINT [FK_Ingredientes_Categoria]
            FOREIGN KEY ([CategoriaId]) REFERENCES [dbo].[Categorias_Ingredientes] ([Id]),
        CONSTRAINT [CK_Ing_UnidadMedida]
            CHECK ([UnidadMedida] IN ('ml','l','g','kg','unidad','pieza','botella','lata')),
        CONSTRAINT [CK_Ing_CantidadActual]   CHECK ([CantidadActual]  >= 0),
        CONSTRAINT [CK_Ing_CantidadMinima]   CHECK ([CantidadMinima]  >= 0),
        CONSTRAINT [CK_Ing_CantidadReorden]  CHECK ([CantidadReorden] >= 0),
        CONSTRAINT [CK_Ing_CostoUnitario]    CHECK ([CostoUnitario]   >= 0)
    );

    CREATE INDEX [IX_Ingredientes_CategoriaId] ON [dbo].[Ingredientes] ([CategoriaId]);
    CREATE INDEX [IX_Ingredientes_Activo]       ON [dbo].[Ingredientes] ([Activo]);

    PRINT 'Table Ingredientes created.';
END
ELSE
    PRINT 'Table Ingredientes already exists. Skipped.';
GO

-- ============================================================
-- PART 4: NEW TABLE — Recetas_Producto (BOM Header)
-- One recipe per product (1:1)
-- ============================================================

IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_NAME = 'Recetas_Producto'
)
BEGIN
    CREATE TABLE [dbo].[Recetas_Producto] (
        [Id]                  INT IDENTITY(1,1)  NOT NULL,
        [ProductoId]          INT                NOT NULL,
        [Descripcion]         NVARCHAR(500)       NULL,
        [Activo]              BIT                 NOT NULL CONSTRAINT [DF_Receta_Activo]       DEFAULT (1),
        [Ultima_Modificacion] DATETIME            NOT NULL CONSTRAINT [DF_Receta_UltimaModif]  DEFAULT GETDATE(),
        CONSTRAINT [PK_Recetas_Producto]  PRIMARY KEY ([Id]),
        CONSTRAINT [UQ_Receta_ProductoId] UNIQUE ([ProductoId]),
        CONSTRAINT [FK_Receta_Producto]
            FOREIGN KEY ([ProductoId]) REFERENCES [dbo].[Productos] ([Id])
    );

    CREATE INDEX [IX_Recetas_ProductoId] ON [dbo].[Recetas_Producto] ([ProductoId]);

    PRINT 'Table Recetas_Producto created.';
END
ELSE
    PRINT 'Table Recetas_Producto already exists. Skipped.';
GO

-- ============================================================
-- PART 5: NEW TABLE — Componentes_Receta (BOM Lines)
-- ============================================================

IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_NAME = 'Componentes_Receta'
)
BEGIN
    CREATE TABLE [dbo].[Componentes_Receta] (
        [Id]                INT IDENTITY(1,1)  NOT NULL,
        [RecetaId]          INT                NOT NULL,
        [IngredienteId]     INT                NOT NULL,
        [CantidadRequerida] NUMERIC(12, 4)      NOT NULL,
        [UnidadMedida]      VARCHAR(20)         NOT NULL,
        CONSTRAINT [PK_Componentes_Receta]  PRIMARY KEY ([Id]),
        CONSTRAINT [FK_Comp_Receta]
            FOREIGN KEY ([RecetaId])      REFERENCES [dbo].[Recetas_Producto] ([Id]),
        CONSTRAINT [FK_Comp_Ingrediente]
            FOREIGN KEY ([IngredienteId]) REFERENCES [dbo].[Ingredientes] ([Id]),
        CONSTRAINT [UQ_Comp_RecetaIngrediente]
            UNIQUE ([RecetaId], [IngredienteId]),
        CONSTRAINT [CK_Comp_CantidadRequerida]
            CHECK ([CantidadRequerida] > 0),
        CONSTRAINT [CK_Comp_UnidadMedida]
            CHECK ([UnidadMedida] IN ('ml','l','g','kg','unidad','pieza','botella','lata'))
    );

    CREATE INDEX [IX_Comp_RecetaId]      ON [dbo].[Componentes_Receta] ([RecetaId]);
    CREATE INDEX [IX_Comp_IngredienteId] ON [dbo].[Componentes_Receta] ([IngredienteId]);

    PRINT 'Table Componentes_Receta created.';
END
ELSE
    PRINT 'Table Componentes_Receta already exists. Skipped.';
GO

-- ============================================================
-- PART 6: NEW TABLE — Movimientos_Ingrediente
-- Full audit ledger for ingredient stock changes
-- ============================================================

IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_NAME = 'Movimientos_Ingrediente'
)
BEGIN
    CREATE TABLE [dbo].[Movimientos_Ingrediente] (
        [Id]                    INT IDENTITY(1,1)  NOT NULL,
        [IngredienteId]         INT                NOT NULL,
        [EmpleadoId]            INT                NULL,
        [TipoMovimiento]        VARCHAR(30)         NOT NULL,
        [Cantidad]              NUMERIC(12, 4)      NOT NULL,
        [CantidadAnterior]      NUMERIC(12, 4)      NOT NULL,
        [CantidadNueva]         NUMERIC(12, 4)      NOT NULL,
        [DocumentoReferencia]   VARCHAR(100)        NULL,
        [PedidoId]              INT                NULL,
        [Notas]                 NVARCHAR(500)       NULL,
        [FechaMovimiento]       DATETIME            NOT NULL CONSTRAINT [DF_MovIng_Fecha] DEFAULT GETDATE(),
        [Movimiento_Local_UUID] VARCHAR(36)         NULL,
        CONSTRAINT [PK_Movimientos_Ingrediente] PRIMARY KEY ([Id]),
        CONSTRAINT [FK_MovIng_Ingrediente]
            FOREIGN KEY ([IngredienteId]) REFERENCES [dbo].[Ingredientes] ([Id]),
        CONSTRAINT [FK_MovIng_Empleado]
            FOREIGN KEY ([EmpleadoId])   REFERENCES [dbo].[Empleados] ([Id]),
        CONSTRAINT [FK_MovIng_Pedido]
            FOREIGN KEY ([PedidoId])     REFERENCES [dbo].[Pedidos_Global] ([Id]),
        CONSTRAINT [CK_MovIng_TipoMovimiento]
            CHECK ([TipoMovimiento] IN (
                'COMPRA', 'AJUSTE_MANUAL', 'CONSUMO_VENTA',
                'DESPERDICIO', 'CORRECCION', 'CARGA_INICIAL', 'DEVOLUCION'
            ))
    );

    CREATE UNIQUE NONCLUSTERED INDEX [IX_MovIng_LocalUUID]
        ON [dbo].[Movimientos_Ingrediente] ([Movimiento_Local_UUID])
        WHERE ([Movimiento_Local_UUID] IS NOT NULL);

    CREATE INDEX [IX_MovIng_IngredienteId]   ON [dbo].[Movimientos_Ingrediente] ([IngredienteId]);
    CREATE INDEX [IX_MovIng_PedidoId]        ON [dbo].[Movimientos_Ingrediente] ([PedidoId]);
    CREATE INDEX [IX_MovIng_FechaMovimiento] ON [dbo].[Movimientos_Ingrediente] ([FechaMovimiento]);
    CREATE INDEX [IX_MovIng_TipoMovimiento]  ON [dbo].[Movimientos_Ingrediente] ([TipoMovimiento]);

    PRINT 'Table Movimientos_Ingrediente created.';
END
ELSE
    PRINT 'Table Movimientos_Ingrediente already exists. Skipped.';
GO

-- ============================================================
-- VERIFICATION QUERY
-- Run after migration to verify all objects exist
-- ============================================================

SELECT
    TABLE_NAME,
    CASE
        WHEN TABLE_NAME IN (
            'Categorias_Ingredientes', 'Ingredientes',
            'Recetas_Producto', 'Componentes_Receta',
            'Movimientos_Ingrediente'
        ) THEN 'NEW (Ingredient System)'
        ELSE 'EXISTING (Legacy)'
    END AS [Status]
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'BASE TABLE'
  AND TABLE_NAME IN (
    'Productos', 'Inventario_Actual', 'Movimientos_Inventario',
    'Categorias_Ingredientes', 'Ingredientes',
    'Recetas_Producto', 'Componentes_Receta', 'Movimientos_Ingrediente'
  )
ORDER BY [Status], TABLE_NAME;
GO

-- Verify the new column on Productos
SELECT
    COLUMN_NAME,
    DATA_TYPE,
    CHARACTER_MAXIMUM_LENGTH,
    COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'Productos'
  AND COLUMN_NAME = 'TipoControlInventario';
GO

PRINT '=== Migration V2 complete. Verify results above. ===';
GO
