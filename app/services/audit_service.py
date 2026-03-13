import json
from sqlmodel import Session
from app.db.database import engine
from app.models.core_models import CoreLog


def log_auditoria(nivel: str, origen: str, mensaje: str, data: dict = None):
    with Session(engine) as session:
        try:
            data_str = json.dumps(data) if data else None

            nuevo_log = CoreLog(
                nivel=nivel,
                origen=origen,
                mensaje=mensaje[:1000],
                data_json=data_str
            )
            session.add(nuevo_log)
            session.commit()
        except Exception as e:
            print(f"Error crítico al escribir en Core_Logs: {e}")