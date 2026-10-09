from datetime import datetime, date
from sqlalchemy import Column, Integer, Date, String, DateTime, Text
from app.db import Base


class BloqueoDia(Base):
    """
    Bloqueo activo para una fecha concreta. Puede ser global (todos los
    trabajadores) o por grupo/identificador (AE6).
    """
    __tablename__ = "bloqueo_dia"

    id = Column(Integer, primary_key=True)
    fecha = Column(Date, nullable=False, index=True)
    motivo = Column(String(200), nullable=True)
    # null -> global; "AE6" -> solo ese grupo
    grupo = Column(String(50), nullable=True, index=True)
    creado_en = Column(DateTime, default=datetime.utcnow, nullable=False)