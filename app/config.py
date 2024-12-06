from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os
load_dotenv()

class Settings(BaseSettings):
    db_user: str
    db_password: str
    db_host: str
    db_port: str
    db_name: str
    clave_secreta: str = os.getenv("CLAVE_SECRETA", "ataque_a_pearl_harbor")

    class Config:
        env_prefix = "DB_"
        env_file = ".env"

settings = Settings()