from sqlmodel import create_engine, Session
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    # ADD THIS TO PREVENT CONTAINERS FROM FREEZING:
    connect_args={
        "login_timeout": 10,  # Fails fast within 10 seconds if Azure SQL takes too long to authenticate
        "timeout": 10        # Fails fast if any individual query gets blocked or hangs
    }
)

def get_session():
    with Session(engine) as session:
        yield session