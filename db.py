from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base
import os

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is required!")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
    # Idempotent column adds for fields introduced after table creation.
    # The DDL below uses PostgreSQL-specific syntax (ADD COLUMN IF NOT EXISTS,
    # ALTER COLUMN ... DROP NOT NULL, partial unique indexes). This project
    # targets PostgreSQL exclusively (Neon-backed), so we gate the migration
    # on the dialect to keep init_db() safe to run under any other engine
    # (e.g. SQLite in local tests where tables are created from scratch and
    # already match the model's nullability).
    if engine.dialect.name != "postgresql":
        return
    from sqlalchemy import text
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE user_preferences "
            "ADD COLUMN IF NOT EXISTS theme VARCHAR(10)"
        ))
        conn.execute(text(
            "ALTER TABLE user_preferences "
            "ADD COLUMN IF NOT EXISTS saas_user_id INTEGER"
        ))
        conn.execute(text(
            "ALTER TABLE user_preferences "
            "ALTER COLUMN user_id DROP NOT NULL"
        ))
        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS "
            "ix_user_preferences_saas_user_id "
            "ON user_preferences(saas_user_id) "
            "WHERE saas_user_id IS NOT NULL"
        ))
        conn.execute(text(
            "ALTER TABLE trips "
            "ADD COLUMN IF NOT EXISTS use_main_boat BOOLEAN NOT NULL DEFAULT TRUE"
        ))
