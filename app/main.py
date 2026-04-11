from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from sqlmodel import SQLModel

from app.api.routers import productos_router, inventario_router, pedidos_router, reportes_router, sync_catalogos_router, sync_usuarios_router, mesa_router, auth_clientes_router, auth_empleados_router
from app.db.database import engine
from app.core.middleware import AuditoriaMiddleware
from app.services.audit_service import log_auditoria
from app.core.security import validate_gateway_token


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

app.include_router(productos_router.router, dependencies=[Depends(validate_gateway_token)])
app.include_router(inventario_router.router, dependencies=[Depends(validate_gateway_token)])
app.include_router(pedidos_router.router, dependencies=[Depends(validate_gateway_token)])
app.include_router(reportes_router.router, dependencies=[Depends(validate_gateway_token)])
app.include_router(sync_catalogos_router.router, dependencies=[Depends(validate_gateway_token)])
app.include_router(sync_usuarios_router.router, dependencies=[Depends(validate_gateway_token)])
app.include_router(mesa_router.router, dependencies=[Depends(validate_gateway_token)])
app.include_router(auth_empleados_router.router, dependencies=[Depends(validate_gateway_token)])
app.include_router(auth_clientes_router.router, dependencies=[Depends(validate_gateway_token)])
