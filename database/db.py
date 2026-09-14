from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from config import settings

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def init_db():
    from database import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    if not settings.DATABASE_URL.startswith("sqlite"):
        return
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("documents")}
    additions = {
        "mime_type": "VARCHAR(150)",
        "is_encrypted": "BOOLEAN NOT NULL DEFAULT 0",
        "sha256": "VARCHAR(64)",
        "extraction_status": "VARCHAR(30) NOT NULL DEFAULT 'pending'",
        "extraction_error": "TEXT",
        "extraction_source": "VARCHAR(30)",
        "extraction_confidence": "VARCHAR(30)",
    }
    with engine.begin() as connection:
        for name, definition in additions.items():
            if name not in columns:
                connection.execute(text(f"ALTER TABLE documents ADD COLUMN {name} {definition}"))
