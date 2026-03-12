from fastapi import FastAPI, Depends
from sqlmodel import text, Session
from app.core.config import settings
from app.db.database import get_session

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API Headless para el sistema central (CORE)"
)

@app.get("/")
def health_check():
    return {"status": "ok", "message": f"Bienvenido a {settings.PROJECT_NAME}"}


@app.get("/test-db")
def test_database_connection(session: Session = Depends(get_session)):
    try:
        statement = text("SELECT 1")
        result = session.exec(statement).first()

        return {
            "status": "success",
            "message": "Conexión a SQL Server exitosa",
            "result": result[0]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}