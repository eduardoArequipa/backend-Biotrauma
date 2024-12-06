import psycopg2
from psycopg2.extras import RealDictCursor
from ..config import settings

def get_db_connection():
    try:
        return psycopg2.connect(
            dbname=settings.db_name,
            user=settings.db_user,
            password=settings.db_password,
            host=settings.db_host,
            port=settings.db_port,
            cursor_factory=RealDictCursor
        )
    except Exception as e:
        print(f"Error conectando a la base de datos: {e}")
        raise e