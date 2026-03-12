import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
from sqlmodel import Session, text, SQLModel

# Importaciones de tu arquitectura (asegúrate de que las rutas sean correctas)
from app.db.database import get_session, engine
from app.models import core_models
from app.core.middleware import AuditoriaMiddleware
from app.services.audit_service import log_auditoria


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestión del ciclo de vida de la aplicación.
    Se ejecuta al iniciar y al apagar el servidor.
    """
    print("🚀 [SISTEMA] Iniciando CORE Mainframe... Verificando tablas en SQL Server.")

    # Sincroniza los modelos con las tablas de la base de datos
    SQLModel.metadata.create_all(engine)

    # Registro inicial de auditoría (Fase 5)
    log_auditoria(
        nivel="INFO",
        origen="SISTEMA",
        mensaje="Servicio CORE iniciado exitosamente."
    )

    yield

    print("🛑 [SISTEMA] Apagando CORE Mainframe...")


# Inicialización de la App
app = FastAPI(
    title="CORE Bar & Lounge API",
    description="Sistema Central de Gestión de Ventas, Inventario y Auditoría",
    version="1.5.0",
    lifespan=lifespan
)

# --- FASE 5: REGISTRO DEL MIDDLEWARE DE AUDITORÍA ---
# Este componente intercepta TODAS las peticiones para guardarlas en Core_Logs
app.add_middleware(AuditoriaMiddleware)


# --- ENDPOINTS DE DIAGNÓSTICO Y PRUEBA DE LÓGICA ---

@app.get("/test-db", tags=["Diagnóstico"])
def test_database_connection(session: Session = Depends(get_session)):
    """
    Prueba básica de conexión a la base de datos.
    Auditoría esperada: INFO.
    """
    try:
        result = session.exec(text("SELECT 1")).first()
        return {
            "status": "success",
            "message": "Conexión a SQL Server exitosa",
            "result": result[0]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/v1/sistema/health", tags=["Lógica y Sistema"])
def revisar_estado_sistema():
    """
    Simula una operación exitosa de la Lógica de Negocio.
    Auditoría esperada: INFO (registrado por el Middleware).
    """
    # Aquí es donde el CORE confirmaría que servicios internos están activos
    return {
        "estado": "OK",
        "mensaje": "CORE Mainframe operando al 100%",
        "fase": 5
    }


@app.get("/api/v1/sistema/simular-error", tags=["Lógica y Sistema"])
def simular_fallo_logica():
    """
    Simula un fallo crítico para probar la robustez del Middleware.
    Auditoría esperada: CRITICAL (con el traceback del error).
    """
    # Provocamos un error matemático para disparar la excepción
    resultado = 1 / 0
    return {"resultado": resultado}