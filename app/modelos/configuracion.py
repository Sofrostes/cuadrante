from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime

from app.db import Base  # ajusta al nombre real de tu Base


class Configuracion(Base):
    __tablename__ = "configuracion"

    clave = Column(String(100), primary_key=True)
    valor = Column(Text, nullable=True)
    descripcion = Column(String(255), nullable=True)
    actualizado_en = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Configuracion {self.clave}={self.valor!r}>"