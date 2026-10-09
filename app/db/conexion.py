from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# El archivo cuadrantes.db vivirá en la raíz del proyecto
RAIZ = Path(__file__).resolve().parent.parent.parent
RUTA_DB = RAIZ / "cuadrantes.db"

engine = create_engine(
    f"sqlite:///{RUTA_DB}",
    echo=False,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def crear_tablas():
    """Crea todas las tablas si no existen."""
    from app.db import modelos  # importamos para que Base las conozca
    modelos.Base.metadata.create_all(bind=engine)


def get_db():
    """Dependencia FastAPI: abre una sesión y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()