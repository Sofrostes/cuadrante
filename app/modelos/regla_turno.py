from sqlalchemy import Column, Integer, String, Boolean
from app.db import Base


class ReglaIncompatibilidad(Base):
    """
    Regla: si un trabajador tiene turno_a el día D, NO puede tener turno_b
    el día D+1.

    Ejemplo típico: turno_a='N' (noche), turno_b='M' (mañana) -> prohibido.
    """
    __tablename__ = "regla_incompatibilidad"

    id = Column(Integer, primary_key=True)
    turno_a = Column(String(10), nullable=False, index=True)
    turno_b = Column(String(10), nullable=False, index=True)
    motivo = Column(String(200), nullable=True)
    activa = Column(Boolean, default=True, nullable=False)