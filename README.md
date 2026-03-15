# CORE MAINFRAME - SISTEMA DE GESTIÓN PARA BARES Y RESTAURANTES

Este proyecto es un backend de alto rendimiento desarrollado con FastAPI y SQLModel. Está diseñado para centralizar la operación comercial de un bar, integrando ventas, inventario y analítica de datos en una sola API transaccional.

---

## 🚀 CARACTERÍSTICAS PRINCIPALES

1.  **Gestión de Ventas:** Ciclo de vida completo del pedido (Apertura -> Carga -> Facturación).
2.  **Cálculo Fiscal Automático:** Aplicación de ITBIS (18%) y Propina Legal (10% - Ley 805) en tiempo real.
3.  **Sincronización de Inventario:** Descuento automático de existencias post-venta con control de stock negativo.
4.  **Trazabilidad (Kardex):** Registro histórico de cada entrada y salida de productos.
5.  **Dashboard Gerencial:** Reportes financieros diarios, ranking de popularidad y alertas de reposición.

---

## 🛠️ REQUISITOS TÉCNICOS Y COMANDOS

### 1. Requisitos de Software
- **Python 3.10+**: Lenguaje de programación base.
- **SQL Server**: Motor de base de datos (Local o Azure).
- **Controlador ODBC**: Drivers para conexión MSSQL (Driver 17 o 18).

### 2. Preparación del Entorno (Comandos)
Ejecute estos comandos en la raíz del proyecto para configurar su entorno:

# Crear el entorno virtual
python -m venv venv

# Activar el entorno
# En Windows:
.\venv\Scripts\activate
# En Linux/Mac:
source venv/bin/activate

# Instalar dependencias necesarias
pip install fastapi uvicorn sqlmodel mssql-django pydantic-settings pyodbc

# (Opcional) Generar archivo de requerimientos para el profesor
pip freeze > requirements.txt

---

## 🔧 CONFIGURACIÓN Y DESPLIEGUE

### Archivo de Entorno (.env)
Cree un archivo llamado `.env` en la raíz del proyecto al mismo nivel que `main.py`. Agregue su cadena de conexión:

DATABASE_URL=mssql+pyodbc://[USUARIO]:[PASSWORD]@[HOST]/[NOMBRE_DB]?driver=ODBC+Driver+17+for+SQL+Server

### Ejecución del Servidor
Para levantar la API con recarga automática:

uvicorn app.main:app --reload

Acceso a la documentación interactiva: http://127.0.0.1:8000/docs

---

## 📂 ESTRUCTURA DEL CÓDIGO (CORE)

- `app/main.py`: Punto de entrada y configuración global de FastAPI.
- `app/api/v1/endpoints/`: Rutas divididas por módulos (Pedidos, Inventario, Reportes).
- `app/models/core_models.py`: Definición de la base de datos (Tablas SQLModel).
- `app/schemas/`: Modelos Pydantic para validación de entrada/salida.
- `app/db/database.py`: Motor de conexión y gestión de sesiones.

---

## 🧪 FLUJO DE PRUEBA DE LA SOLUCIÓN

Para validar el funcionamiento completo de la Fase 1 a la 12:

1.  **Configurar Almacén:** Crear un producto y cargar stock inicial en el módulo de Inventario.
2.  **Transacción:** Abrir un pedido en una mesa, agregar el producto y ejecutar `/facturar`.
3.  **Validación Logística:** Consultar el inventario para confirmar el descuento automático.
4.  **Analítica:** Abrir el Dashboard de Reportes para ver el impacto en las ventas del día.
