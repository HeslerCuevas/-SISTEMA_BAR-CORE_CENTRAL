from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from sqlmodel import SQLModel
from fastapi.openapi.utils import get_openapi

from app.api.routers import productos_router, inventario_router, pedidos_router, reportes_router, mesa_router, auth_clientes_router, auth_empleados_router, empleados_router, sucursales_router, roles_router
from app.api.routers import clientes_admin_router, promociones_router, ncf_router

from app.db.database import engine
from app.core.middleware import AuditoriaMiddleware
from app.services.audit_service import log_auditoria
from app.core.security import validate_gateway_token
from fastapi.security import APIKeyHeader


gateway_token_scheme = APIKeyHeader(
    name="X-Gateway-Token",
    description="Introduce el token secreto del Gateway (CORE_SECRET_KEY)"
)

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
    description="Sistema Central de Gestión de Ventas, Inventario, Auditoría y Administración",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(AuditoriaMiddleware)

# ─── Routers existentes ──────────────────────────────────────────────────────
app.include_router(productos_router.router, dependencies=[Depends(validate_gateway_token)])
app.include_router(inventario_router.router, dependencies=[Depends(validate_gateway_token)])
app.include_router(pedidos_router.router, dependencies=[Depends(validate_gateway_token)])
app.include_router(reportes_router.router, dependencies=[Depends(validate_gateway_token)])
app.include_router(mesa_router.router, dependencies=[Depends(validate_gateway_token)])
app.include_router(auth_empleados_router.router, dependencies=[Depends(validate_gateway_token)])
app.include_router(auth_clientes_router.router, dependencies=[Depends(validate_gateway_token)])
app.include_router(empleados_router.router, dependencies=[Depends(validate_gateway_token)])
app.include_router(roles_router.router, dependencies=[Depends(validate_gateway_token)])
app.include_router(sucursales_router.router, dependencies=[Depends(validate_gateway_token)])
app.include_router(clientes_admin_router.router, dependencies=[Depends(validate_gateway_token)])
app.include_router(promociones_router.router, dependencies=[Depends(validate_gateway_token)])
app.include_router(ncf_router.router, dependencies=[Depends(validate_gateway_token)])


from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    if "components" not in openapi_schema:
        openapi_schema["components"] = {}

    # 1. Definimos los componentes usando nombres normalizados
    openapi_schema["components"]["securitySchemes"] = {
        "GatewayTokenAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "x-gateway-token",  # Usamos minúsculas estándar para evitar duplicados en curl
            "description": "Introduce el token secreto del Gateway (CORE_SECRET_KEY)"
        },
        "OAuth2PasswordBearer": {
            "type": "oauth2",
            "flows": {
                "password": {
                    "tokenUrl": "/api/v1/auth/login",
                    "scopes": {}
                }
            }
        }
    }

    # 2. Declaramos la seguridad secuencial alternativa.
    # Esto le dice a Swagger que CUALQUIER endpoint puede validarse con la combinación
    # [Gateway + Bearer] O con [Solo Gateway] (para permitir el login inicial).
    openapi_schema["security"] = [
        {
            "GatewayTokenAuth": [],
            "OAuth2PasswordBearer": []
        },
        {
            "GatewayTokenAuth": []
        }
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi