import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tutormind.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def run_migrations() -> None:
    """Añade columnas/tablas nuevas en SQLite sin perder datos existentes."""
    inspector = inspect(engine)
    if "users" in inspector.get_table_names():
        user_cols = {col["name"] for col in inspector.get_columns("users")}
        with engine.begin() as conn:
            if "password_hash" not in user_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"))
            if "role" not in user_cols:
                conn.execute(
                    text("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'student'")
                )
                conn.execute(text("UPDATE users SET role = 'student' WHERE role IS NULL"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
