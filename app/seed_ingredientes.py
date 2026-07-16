"""
seed_ingredientes.py
====================
Script en Python para limpiar y poblar todas las tablas del sistema de
Productos e Ingredientes en la base de datos Core_Master_DB.

Este script ejecuta:
  1. Limpieza total de tablas relacionadas (respetando restricciones FK).
  2. Reseteo de contadores de identidad (RESEED).
  3. Registro de Impuestos (ITBIS).
  4. Registro de Categorías de Productos.
  5. Registro de Productos (incluyendo SKU, Nombre, Descripción, Precio,
     EsInventariable, Active e ImagenURL).
  6. Inicialización del Inventario de Productos (Legacy/Unidad).
  7. Registro de Categorías de Ingredientes e Ingredientes.
  8. Registro de Recetas y sus Componentes.
  9. Inicialización de Inventario de Ingredientes (Movimientos).

Ejecución:
    python app/seed_ingredientes.py
"""

import os
import sys
from datetime import datetime
from urllib.parse import unquote
import pyodbc
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Ajuste del path de importación
# ---------------------------------------------------------------------------
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

load_dotenv(os.path.join(ROOT_DIR, ".env"))

# ---------------------------------------------------------------------------
# Configuración de conexión pyodbc a partir del .env
# ---------------------------------------------------------------------------
def get_connection():
    db_url = os.getenv("DATABASE_URL", "")
    if "odbc_connect=" in db_url:
        odbc_str = db_url.split("odbc_connect=", 1)[1]
        odbc_str = unquote(odbc_str)
    else:
        # Fallback local o docker en caso de ausencia
        odbc_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=LAPTOP-E8Q0ITLB\\INTEC_INS380L;"
            "DATABASE=Core_Master_DB;"
            "Trusted_Connection=yes;"
        )
    return pyodbc.connect(odbc_str, autocommit=False)


# ---------------------------------------------------------------------------
# DATOS A INSERTAR
# ---------------------------------------------------------------------------

IMPUESTOS = [
    (1, "ITBIS", 18.00, 1)
]

CATEGORIAS = [
    (1, "Cervezas"),
    (2, "Cócteles"),
    (3, "Comida"),
    (4, "Vinos"),
    (5, "Sin Alcohol")
]

# (Id, CategoriaId, ImpuestoId, SKU, Nombre, Descripcion, PrecioBase, TipoControlInventario, Active, ImagenURL)
PRODUCTOS = [
    (1, 1, 1, 'B-01', 'Presidente Light', 'Bien fría, 12oz.', 195.00, 'PRODUCTO', 1, 'https://images.unsplash.com/photo-1535958636474-b021ee887b13?q=80&w=600&auto=format&fit=crop'),
    (2, 2, 1, 'COCK-01', 'Margarita Clásica', 'Tequila, triple sec y limón.', 350.00, 'INGREDIENTES', 1, 'https://images.unsplash.com/photo-1536935338788-846bb9981813?q=80&w=400&auto=format&fit=crop'),
    (3, 2, 1, 'COCK-02', 'Mojito Tradicional', 'Ron blanco, menta y azúcar.', 325.00, 'INGREDIENTES', 1, 'https://images.unsplash.com/photo-1551538827-9c037cb4f32a?q=80&w=400&auto=format&fit=crop'),
    (4, 2, 1, 'COCK-03', 'Piña Colada', 'Ron, crema de coco y piña.', 375.00, 'INGREDIENTES', 1, 'https://images.unsplash.com/photo-1546171753-97d7676e4602?q=80&w=400&auto=format&fit=crop'),
    (5, 3, 1, 'FOOD-01', 'Alitas Buffalo', '6 alitas con aderezo ranch.', 450.00, 'INGREDIENTES', 1, 'https://images.unsplash.com/photo-1567620832903-9fc6debc209f?q=80&w=400&auto=format&fit=crop'),
    (6, 3, 1, 'FOOD-02', 'Nachos Supremos', 'Con queso, carne y jalapeños.', 550.00, 'INGREDIENTES', 1, 'https://images.unsplash.com/photo-1513456852971-30c0b8199d4d?q=80&w=400&auto=format&fit=crop'),
    (7, 3, 1, 'FOOD-03', 'Papas Fritas', 'Crocantes con sal marina.', 250.00, 'INGREDIENTES', 1, 'https://images.unsplash.com/photo-1573080496219-bb080dd4f877?q=80&w=400&auto=format&fit=crop'),
    (8, 4, 1, 'WINE-01', 'Copa Vino Tinto', 'Cabernet Sauvignon de la casa.', 290.00, 'PRODUCTO', 1, 'https://images.unsplash.com/photo-1510812431401-41d2bd2722f3?q=80&w=400&auto=format&fit=crop'), 
    (9, 5, 1, 'D-02', 'Agua Mineral', 'Botella 500ml.', 75.00, 'PRODUCTO', 1, 'https://images.unsplash.com/photo-1523362628745-0c100150b504?q=80&w=600&auto=format&fit=crop'),
    (10, 2, 1, 'C-04', 'Old Fashioned', 'Whiskey, amargo y piel de naranja.', 425.00, 'INGREDIENTES', 1, 'https://images.unsplash.com/photo-1470337458703-46ad1756a187?q=80&w=600&auto=format&fit=crop')
]

CATEGORIAS_INGREDIENTES = [
    (1, "Licores Base",       "Destilados principales: ron, tequila, whiskey, vodka, etc."),
    (2, "Licores y Cordiales","Licores de sabor: Triple Sec, Baileys, etc."),
    (3, "Jugos y Frutas",     "Jugos y frutas frescas para coctelería."),
    (4, "Soda y Agua",        "Aguas carbonatadas y sodas."),
    (5, "Lácteos y Cremas",   "Crema de coco, leches, etc."),
    (6, "Hierbas y Especias", "Menta, twists y aromáticos."),
    (7, "Endulzantes",        "Azúcar, jarabe simple y miel."),
    (8, "Amargos y Bitters",  "Angostura y otros bitters."),
    (9, "Proteínas y Carnes", "Alitas, carne y proteínas de cocina."),
    (10,"Snacks y Frituras",  "Tortillas y papas crudas."),
    (11,"Lácteos Cocina",     "Queso, aderezo ranch, crema agria."),
    (12,"Vegetales",          "Jalapeños y salsas para cocina."),
]

INGREDIENTES = [
    (1,  1, "Ron Blanco",          "Ron blanco estándar para coctelería.",   "ml", 4500.0, 750.0, 1500.0, 0.28),
    (2,  1, "Tequila Blanco",      "Tequila 100% agave para Margaritas.",    "ml", 3000.0, 750.0, 1500.0, 0.42),
    (3,  1, "Whiskey Bourbon",     "Bourbon americano para Old Fashioned.",  "ml", 2250.0, 750.0, 1500.0, 0.50),
    (4,  2, "Triple Sec",          "Licor de naranja.",                      "ml", 1500.0, 375.0,  750.0, 0.35),
    (5,  2, "Crema de Coco",       "Crema de coco espesa para Piña Colada.",  "ml", 1000.0, 250.0,  500.0, 0.30),
    (6,  3, "Jugo de Limón",       "Jugo de limón fresco exprimido.",        "ml", 2000.0, 500.0, 1000.0, 0.05),
    (7,  3, "Jugo de Piña",        "Jugo de piña natural.",                  "ml", 2000.0, 500.0, 1000.0, 0.08),
    (8,  4, "Agua con Gas",        "Agua carbonatada (club soda).",          "ml", 3000.0, 600.0, 1200.0, 0.03),
    (9,  6, "Menta Fresca",        "Hojas de menta/hierbabuena.",            "g",   500.0,  80.0,  150.0, 0.10),
    (10, 6, "Piel de Naranja",     "Twist de naranja para decoración.",      "unidad",100.0, 20.0,   50.0, 0.15),
    (11, 7, "Azúcar Blanca",       "Azúcar estándar.",                       "g",  2000.0, 300.0,  600.0, 0.002),
    (12, 7, "Jarabe Simple",       "Jarabe de azúcar 1:1.",                  "ml", 1500.0, 250.0,  500.0, 0.04),
    (13, 8, "Angostura Bitters",   "Bitters aromáticos Angostura.",          "ml",  120.0,  30.0,   60.0, 1.20),
    (14, 9, "Alitas de Pollo",     "Alitas de pollo frescas.",               "unidad",60.0, 12.0,   24.0, 35.00),
    (15, 9, "Carne Molida",        "Carne molida de res.",                   "g",  1500.0, 300.0,  600.0, 0.18),
    (16,10, "Tortillas de Maíz",   "Chips de tortilla.",                     "g",  2000.0, 400.0,  800.0, 0.04),
    (17,10, "Papas Crudas",        "Papas para freír.",                      "g",  5000.0, 800.0, 1600.0, 0.03),
    (18,11, "Queso Cheddar",       "Queso cheddar rallado.",                 "g",  1000.0, 200.0,  400.0, 0.12),
    (19,11, "Aderezo Ranch",       "Aderezo ranch.",                         "ml",  600.0, 100.0,  200.0, 0.08),
    (20,11, "Crema Agria",         "Crema agria.",                           "ml",  400.0,  80.0,  160.0, 0.07),
    (21,12, "Jalapeños en Rodajas","Jalapeños en escabeche.",                "g",   600.0, 100.0,  200.0, 0.06),
    (22,12, "Salsa Buffalo",       "Salsa picante estilo Buffalo.",          "ml",  800.0, 150.0,  300.0, 0.09),
]

RECETAS = [
    (2,  "Margarita Clásica — receta estándar de coctelería."),
    (3,  "Mojito Tradicional — receta clásica de la isla."),
    (4,  "Piña Colada — tropical y cremoso."),
    (5,  "Alitas Buffalo — 6 piezas con aderezo ranch."),
    (6,  "Nachos Supremos — con queso fundido, carne y jalapeños."),
    (7,  "Papas Fritas — porción individual crocante."),
    (10, "Old Fashioned — whiskey, amargo y piel de naranja."),
]

COMPONENTES = {
    2:  [
        (2,  60.0,  "ml"),      # Tequila Blanco
        (4,  30.0,  "ml"),      # Triple Sec
        (6,  30.0,  "ml"),      # Jugo de Limón
        (12, 15.0,  "ml"),      # Jarabe Simple
    ],
    3:  [
        (1,  60.0,  "ml"),      # Ron Blanco
        (6,  30.0,  "ml"),      # Jugo de Limón
        (11, 20.0,  "g"),       # Azúcar Blanca
        (9,  10.0,  "g"),       # Menta Fresca
        (8,  90.0,  "ml"),      # Agua con Gas
    ],
    4:  [
        (1,  60.0,  "ml"),      # Ron Blanco
        (5,  60.0,  "ml"),      # Crema de Coco
        (7,  120.0, "ml"),      # Jugo de Piña
    ],
    5:  [
        (14, 6.0,   "unidad"),  # Alitas de Pollo
        (22, 60.0,  "ml"),      # Salsa Buffalo
        (19, 40.0,  "ml"),      # Aderezo Ranch
    ],
    6:  [
        (16, 150.0, "g"),       # Tortillas de Maíz
        (15, 100.0, "g"),       # Carne Molida
        (18, 80.0,  "g"),       # Queso Cheddar
        (21, 30.0,  "g"),       # Jalapeños
        (20, 30.0,  "ml"),      # Crema Agria
    ],
    7:  [
        (17, 200.0, "g"),       # Papas Crudas
    ],
    10: [
        (3,  60.0,  "ml"),      # Whiskey Bourbon
        (13, 4.0,   "ml"),      # Angostura Bitters
        (12, 10.0,  "ml"),      # Jarabe Simple
        (10, 1.0,   "unidad"),  # Piel de Naranja
    ],
}


# ---------------------------------------------------------------------------
# EJECUCIÓN DEL SEED
# ---------------------------------------------------------------------------

def seed_database():
    print("=" * 70)
    print("  INICIALIZACIÓN COMPLETA · PRODUCTOS E INGREDIENTES")
    print("=" * 70)

    try:
        conn = get_connection()
        cursor = conn.cursor()
        print("\n[✓] Conexión establecida con la base de datos.")

        # -------------------------------------------------------------------
        # 1. LIMPIEZA DE TABLAS (Evitando violaciones FK)
        # -------------------------------------------------------------------
        print("\n[1/9] Limpiando tablas existentes...")
        tables_to_clean = [
            "[dbo].[Detalles_Pedido]",
            "[dbo].[Movimientos_Inventario]",
            "[dbo].[Inventario_Actual]",
            "[dbo].[Componentes_Receta]",
            "[dbo].[Recetas_Producto]",
            "[dbo].[Movimientos_Ingrediente]",
            "[dbo].[Ingredientes]",
            "[dbo].[Categorias_Ingredientes]",
            "[dbo].[Productos]",
            "[dbo].[Categorias]",
            "[dbo].[Impuestos]"
        ]
        for table in tables_to_clean:
            cursor.execute(f"DELETE FROM {table}")
            print(f"      - {table} vaciada.")

        # -------------------------------------------------------------------
        # 2. RESETEANDO CONTADORES DE IDENTIDAD
        # -------------------------------------------------------------------
        print("\n[2/9] Reseteando contadores de identidad (IDENTITY)...")
        tables_to_reseed = [
            "[dbo].[Categorias]",
            "[dbo].[Impuestos]",
            "[dbo].[Productos]",
            "[dbo].[Categorias_Ingredientes]",
            "[dbo].[Ingredientes]",
            "[dbo].[Recetas_Producto]",
            "[dbo].[Componentes_Receta]",
            "[dbo].[Movimientos_Ingrediente]"
        ]
        for table in tables_to_reseed:
            try:
                cursor.execute(f"DBCC CHECKIDENT ('{table}', RESEED, 0)")
            except Exception:
                # Si una tabla no tiene columna IDENTITY, omitir
                pass
        print("      ✓ Contadores reiniciados.")

        # -------------------------------------------------------------------
        # 3. IMPUESTOS
        # -------------------------------------------------------------------
        print("\n[3/9] Insertando Impuestos...")
        cursor.execute("SET IDENTITY_INSERT [dbo].[Impuestos] ON")
        for imp_id, nombre, tasa, activo in IMPUESTOS:
            cursor.execute(
                "INSERT INTO [dbo].[Impuestos] (Id, Nombre, TasaPorcentaje, Active) VALUES (?, ?, ?, ?)",
                imp_id, nombre, tasa, activo
            )
            print(f"      ✓ Impuesto [{imp_id}] {nombre} ({tasa}%)")
        cursor.execute("SET IDENTITY_INSERT [dbo].[Impuestos] OFF")

        # -------------------------------------------------------------------
        # 4. CATEGORÍAS DE PRODUCTO
        # -------------------------------------------------------------------
        print("\n[4/9] Insertando Categorías de Producto...")
        cursor.execute("SET IDENTITY_INSERT [dbo].[Categorias] ON")
        for cat_id, nombre in CATEGORIAS:
            cursor.execute(
                "INSERT INTO [dbo].[Categorias] (Id, Nombre, Active) VALUES (?, ?, 1)",
                cat_id, nombre
            )
            print(f"      ✓ Categoría [{cat_id}] {nombre}")
        cursor.execute("SET IDENTITY_INSERT [dbo].[Categorias] OFF")

        # -------------------------------------------------------------------
        # 5. PRODUCTOS (Con ImagenURL e información completa)
        # -------------------------------------------------------------------
        print("\n[5/9] Insertando Productos (incluyendo ImagenURL)...")
        cursor.execute("SET IDENTITY_INSERT [dbo].[Productos] ON")
        for row in PRODUCTOS:
            cursor.execute(
                """
                INSERT INTO [dbo].[Productos] 
                    (Id, CategoriaId, ImpuestoId, SKU, Nombre, Descripcion, 
                     PrecioBase, TipoControlInventario, Active, ImagenURL)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9]
            )
            print(f"      ✓ Product [{row[0]}] '{row[4]}' | SKU: {row[3]} | URL: {row[9][:45]}...")
        cursor.execute("SET IDENTITY_INSERT [dbo].[Productos] OFF")

        # -------------------------------------------------------------------
        # 6. INVENTARIO ACTUAL Y MOVIMIENTOS (De los productos inventariables a nivel unitario)
        # -------------------------------------------------------------------
        print("\n[6/9] Inicializando inventario base (Productos unitarios)...")
        cursor.execute(
            """
            INSERT INTO [dbo].[Inventario_Actual] (ProductoId, CantidadDisponible, StockMinimo, UltimaActualizacion)
            SELECT Id, 50, 5, GETDATE() 
            FROM [dbo].[Productos] 
            WHERE TipoControlInventario = 'PRODUCTO';
            """
        )
        cursor.execute(
            """
            INSERT INTO [dbo].[Movimientos_Inventario] (ProductoId, EmpleadoId, TipoMovimiento, Cantidad, Motivo, FechaMovimiento)
            SELECT Id, NULL, 'ENTRADA', 50, 'Carga inicial post-limpieza', GETDATE() 
            FROM [dbo].[Productos] 
            WHERE TipoControlInventario = 'PRODUCTO';
            """
        )
        print("      ✓ Inventario y movimientos iniciales creados para productos inventariables.")

        # -------------------------------------------------------------------
        # 7. CATEGORÍAS DE INGREDIENTES E INGREDIENTES
        # -------------------------------------------------------------------
        print("\n[7/9] Insertando Categorías de Ingredientes e Ingredientes...")
        cursor.execute("SET IDENTITY_INSERT [dbo].[Categorias_Ingredientes] ON")
        for cat_id, nombre, desc in CATEGORIAS_INGREDIENTES:
            cursor.execute(
                "INSERT INTO [dbo].[Categorias_Ingredientes] (Id, Nombre, Descripcion, Active) VALUES (?, ?, ?, 1)",
                cat_id, nombre, desc
            )
        cursor.execute("SET IDENTITY_INSERT [dbo].[Categorias_Ingredientes] OFF")
        print(f"      ✓ {len(CATEGORIAS_INGREDIENTES)} categorías de ingredientes creadas.")

        cursor.execute("SET IDENTITY_INSERT [dbo].[Ingredientes] ON")
        for row in INGREDIENTES:
            cursor.execute(
                """
                INSERT INTO [dbo].[Ingredientes]
                    (Id, CategoriaId, Nombre, Descripcion, UnidadMedida,
                     CantidadActual, CantidadMinima, CantidadReorden, CostoUnitario, Active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8]
            )
        cursor.execute("SET IDENTITY_INSERT [dbo].[Ingredientes] OFF")
        print(f"      ✓ {len(INGREDIENTES)} ingredientes creados con su stock base.")

        # -------------------------------------------------------------------
        # 8. RECETAS Y COMPONENTES
        # -------------------------------------------------------------------
        print("\n[8/9] Registrando Recetas y sus Componentes...")
        for prod_id, desc in RECETAS:
            cursor.execute(
                "INSERT INTO [dbo].[Recetas_Producto] (ProductoId, Descripcion, Active) VALUES (?, ?, 1)",
                prod_id, desc
            )
        
        # Obtener mapeo de recetas creadas para relacionar componentes
        cursor.execute("SELECT Id, ProductoId FROM [dbo].[Recetas_Producto]")
        receta_map = {row[1]: row[0] for row in cursor.fetchall()}

        comp_count = 0
        for prod_id, componentes in COMPONENTES.items():
            rec_id = receta_map.get(prod_id)
            if not rec_id:
                continue
            for ing_id, cant, unidad in componentes:
                cursor.execute(
                    """
                    INSERT INTO [dbo].[Componentes_Receta] (RecetaId, IngredienteId, CantidadRequerida, UnidadMedida)
                    VALUES (?, ?, ?, ?)
                    """,
                    rec_id, ing_id, cant, unidad
                )
                comp_count += 1
        
        print(f"      ✓ {len(RECETAS)} recetas creadas con {comp_count} componentes en total.")

        # -------------------------------------------------------------------
        # 9. MOVIMIENTOS DE CARGA INICIAL PARA INGREDIENTES
        # -------------------------------------------------------------------
        print("\n[9/9] Creando historial de movimientos de carga inicial...")
        for row in INGREDIENTES:
            ing_id, _, nombre, _, _, cant_actual, _, _, _ = row
            cursor.execute(
                """
                INSERT INTO [dbo].[Movimientos_Ingrediente]
                    (IngredienteId, EmpleadoId, TipoMovimiento, Cantidad, CantidadAnterior, CantidadNueva, Notas)
                VALUES (?, NULL, 'CARGA_INICIAL', ?, 0, ?, 'Carga inicial del sistema de ingredientes')
                """,
                ing_id, cant_actual, cant_actual
            )
        print("      ✓ Movimientos iniciales de auditoría registrados.")

        # -------------------------------------------------------------------
        # CONFIRMACIÓN Y COMMIT
        # -------------------------------------------------------------------
        conn.commit()
        print("\n" + "=" * 70)
        print("  ✅ TODO POBLADO CON ÉXITO. CAMBIOS APLICADOS (COMMIT).")
        print("=" * 70)

    except Exception as e:
        conn.rollback()
        print("\n" + "=" * 70)
        print(f"  ❌ ERROR EN EL SEED — SE HIZO ROLLBACK DE TODA LA TRANSACCIÓN.")
        print(f"  Detalle: {e}")
        print("=" * 70)
        raise
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    seed_database()
