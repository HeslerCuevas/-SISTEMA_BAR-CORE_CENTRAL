import time
import traceback
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.services.audit_service import log_auditoria

class AuditoriaMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        origen = f"{request.method} {request.url.path}"

        rutas_ignoradas = ["/docs", "/redoc", "/openapi.json"]
        if any(request.url.path.startswith(ruta) for ruta in rutas_ignoradas):
            return await call_next(request)

        start_time = time.time()

        try:
            response = await call_next(request)

            process_time = time.time() - start_time

            nivel = "INFO" if response.status_code < 400 else "WARNING"
            log_auditoria(
                nivel=nivel,
                origen=origen,
                mensaje=f"Transacción completada con estado {response.status_code}",
                data={"tiempo_ejecucion_segundos": round(process_time, 4)}
            )
            return response

        except Exception as e:
            process_time = time.time() - start_time
            trace = traceback.format_exc()

            log_auditoria(
                nivel="CRITICAL",
                origen=origen,
                mensaje=f"Fallo en Lógica de Negocio: {str(e)}",
                data={"tiempo_ejecucion": round(process_time, 4), "traceback": trace}
            )
            raise e