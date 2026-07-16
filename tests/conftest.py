import pytest
import time
import os
from datetime import timedelta
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
import uuid

@compiles(UNIQUEIDENTIFIER, "sqlite")
def compile_uniqueidentifier(type_, compiler, **kw):
    return "VARCHAR(36)"

original_bind_processor = UNIQUEIDENTIFIER.bind_processor

def patched_bind_processor(self, dialect):
    if dialect.name == "sqlite":
        def process(value):
            if value is None:
                return None
            if isinstance(value, uuid.UUID):
                return str(value)
            return str(value)
        return process
    return original_bind_processor(self, dialect)

UNIQUEIDENTIFIER.bind_processor = patched_bind_processor

from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine

# Overwrite environment variables before importing app components
os.environ["DATABASE_URL_LOCAL"] = "sqlite:///./test_core.db"
os.environ["CORE_SECRET_KEY"] = "super_secret_test_key"
os.environ["PROJECT_NAME"] = "TEST CORE API"

# Import engine and app after setting env vars
from app.db.database import get_session
from app.main import app

# Create a clean SQLite database engine for testing
test_engine = create_engine("sqlite:///./test_core.db", connect_args={"check_same_thread": False}, echo=False)

from sqlalchemy import event
import datetime

@event.listens_for(test_engine, "connect")
def register_sqlite_functions(dbapi_connection, connection_record):
    # Map MSSQL GETDATE() to SQLite
    dbapi_connection.create_function("GETDATE", 0, lambda: datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    dbapi_connection.create_function("sysdatetime", 0, lambda: datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'))

def override_get_session():
    with Session(test_engine) as session:
        yield session

app.dependency_overrides[get_session] = override_get_session

# Mock engine in audit_service so log_auditoria uses test_engine
import app.services.audit_service as audit_service
audit_service.engine = test_engine

# Also overwrite the actual module's engine just to be perfectly sure
import app.db.database as app_db
app_db.engine = test_engine
app_db.get_session = override_get_session

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    SQLModel.metadata.drop_all(test_engine)
    SQLModel.metadata.create_all(test_engine)
    yield
    SQLModel.metadata.drop_all(test_engine)
    if os.path.exists("./test_core.db"):
        try:
            os.remove("./test_core.db")
        except Exception:
            pass

@pytest.fixture(scope="function")
def db_session():
    with Session(test_engine) as session:
        yield session

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def admin_token_header(client: TestClient, db_session):
    from app.models.core_models import Rol, Empleado
    from app.core.security import get_password_hash
    
    rol = db_session.query(Rol).filter(Rol.nombre == "ADMIN").first()
    if not rol:
        rol = Rol(nombre="ADMIN")
        db_session.add(rol)
        db_session.commit()
        db_session.refresh(rol)

    emp = db_session.query(Empleado).filter(Empleado.email == "admin_global@test.com").first()
    if not emp:
        emp = Empleado(
            nombre_completo="Admin Global",
            email="admin_global@test.com",
            documento_identidad="GLOBAL_ADMIN",
            password_hash=get_password_hash("password123"),
            rol_id=rol.id,
            activo=True,
            sucursal_id=1
        )
        db_session.add(emp)
        db_session.commit()
        db_session.refresh(emp)

    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin_global@test.com", "password": "password123"},
        headers={"X-Gateway-Token": "super_secret_test_key"}
    )
    token = response.json()["access_token"]
    return {
        "X-Gateway-Token": "super_secret_test_key",
        "Authorization": f"Bearer {token}"
    }


# --- Custom Reporting Logic ---
# To match the requested output format precisely

def pytest_configure(config):
    config.test_results = {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "total": 0,
        "start_time": time.time(),
        "failed_tests": []
    }

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    report.start_time = call.start if hasattr(call, 'start') else time.time()
    report.duration = call.stop - call.start if hasattr(call, 'stop') and hasattr(call, 'start') else getattr(report, 'duration', 0)

@pytest.hookimpl(tryfirst=True)
def pytest_report_teststatus(report, config):
    if report.when == "call":
        config.test_results["total"] += 1
        
        test_name = report.nodeid.split("::")[-1].replace("_", " ").title()
        
        print("\n==================================================")
        print(f"TEST: {test_name}")
        
        duration_ms = int(report.duration * 1000)
        
        if report.passed:
            config.test_results["passed"] += 1
            print("STATUS: PASSED")
            print(f"Duration: {duration_ms} ms")
        elif report.failed:
            config.test_results["failed"] += 1
            config.test_results["failed_tests"].append(test_name)
            print("STATUS: FAILED")
            print("Reason:")
            if hasattr(report, 'longreprtext'):
                # Extract a short reason if possible
                lines = report.longreprtext.split('\n')
                for line in reversed(lines):
                    if "HTTP" in line or "AssertionError" in line or "Exception" in line:
                        print(line.strip())
                        break
                else:
                    print("Test execution failed (AssertionError or Exception)")
            print(f"Duration: {duration_ms} ms")
        elif report.skipped:
            config.test_results["skipped"] += 1
            print("STATUS: SKIPPED")
            
        print("==================================================")
        
    return outcome if 'outcome' in locals() else None # Suppress standard dot output

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    terminalreporter.write_line("")
    terminalreporter.write_line("====================================")
    terminalreporter.write_line("TEST EXECUTION SUMMARY")
    terminalreporter.write_line("====================================")
    terminalreporter.write_line("")
    terminalreporter.write_line(f"Total Tests: {config.test_results['total']}")
    terminalreporter.write_line("")
    terminalreporter.write_line(f"Passed: {config.test_results['passed']}")
    terminalreporter.write_line("")
    terminalreporter.write_line(f"Failed: {config.test_results['failed']}")
    terminalreporter.write_line("")
    terminalreporter.write_line(f"Skipped: {config.test_results['skipped']}")
    terminalreporter.write_line("")
    
    total_duration = time.time() - config.test_results["start_time"]
    td = timedelta(seconds=int(total_duration))
    minutes, seconds = divmod(td.seconds, 60)
    terminalreporter.write_line("Execution Time:")
    if minutes > 0:
        terminalreporter.write_line(f"{minutes}m {seconds}s")
    else:
        terminalreporter.write_line(f"{seconds}s")
    
    if config.test_results["failed"] > 0:
        terminalreporter.write_line("")
        terminalreporter.write_line("Failed Tests:")
        terminalreporter.write_line("")
        for test in config.test_results["failed_tests"]:
            terminalreporter.write_line(f"• {test}")
            
    terminalreporter.write_line("")


# --- Mock email sending for tests ---
from unittest.mock import patch

@pytest.fixture(scope="function", autouse=True)
def mock_enviar_email():
    with patch("app.services.email_service._enviar_email", return_value=None), \
         patch("app.services.email_service.enviar_email_reset_password", return_value=None):
        yield
