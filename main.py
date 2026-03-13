import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
from sqlmodel import Session, text, SQLModel

from app.api.routers import productos_router
from app.api.routers import inventario_router
from app.db.database import get_session, engine
from app.models import core_models
from app.core.middleware import AuditoriaMiddleware
from app.services.audit_service import log_auditoria


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[SISTEMA] Iniciando CORE Mainframe... Verificando tablas en SQL Server.")

    SQLModel.metadata.create_all(engine)

    log_auditoria(
        nivel="INFO",
        origen="SISTEMA",
        mensaje="Servicio CORE iniciado exitosamente."
    )

    yield

    print("[SISTEMA] Apagando CORE Mainframe...")


app = FastAPI(
    title="CORE Bar & Lounge API",
    description="Sistema Central de Gestión de Ventas, Inventario y Auditoría",
    version="1.5.0",
    lifespan=lifespan
)

app.add_middleware(AuditoriaMiddleware)
app.include_router(productos_router.router)
app.include_router(inventario_router.router)

@app.get("/test-db", tags=["Diagnóstico"])
def test_database_connection(session: Session = Depends(get_session)):
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
    return {
        "estado": "OK",
        "mensaje": "CORE Mainframe operando al 100%",
        "fase": 5
    }


@app.get("/api/v1/sistema/simular-error", tags=["Lógica y Sistema"])
def simular_fallo_logica():
    resultado = 1 / 0
    return {"resultado": resultado}