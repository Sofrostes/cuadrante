from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text

from app.db import Base


class VolcadoEstado(Base):
    """
    Estado de volcado a Excel por entidad.

    `clave` es el identificador externo de lo que estás volcando
    (id numérico, DNI, código, etc.). Guardamos una fila por clave.
    """

    __tablename__ = "volcado_estado"

    id = Column(Integer, primary_key=True)
    clave = Column(String(200), nullable=False, unique=True, index=True)

    volcado_ok = Column(Boolean, nullable=False, default=False, index=True)
    volcado_error = Column(Text, nullable=True)
    intentos = Column(Integer, nullable=False, default=0)
    ultimo_intento_en = Column(DateTime, nullable=True)
    volcado_ok_en = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<VolcadoEstado {self.clave} ok={self.volcado_ok}>"