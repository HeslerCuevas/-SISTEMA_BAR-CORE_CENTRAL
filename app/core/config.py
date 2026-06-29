import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "CORE API")
    VERSION: str = os.getenv("VERSION", "2.0.0")
    DATABASE_URL: str = os.getenv("DATABASE_URL_LOCAL")

settings = Settings()