from sqlalchemy import (
    Column, Integer, String, Boolean, Date, DateTime, ForeignKey, Text, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


# ------------------------------------------------------------------
# CATÁLOGOS
# ------------------------------------------------------------------

class Zona(Base):
    __tablename__ = "zonas"
    id = Column(Integer, primary_key=True)
    codigo = Column(String(20), unique=True, nullable=False)   # AE6, AE7, AE8...
    nombre = Column(String(200), nullable=False)                # ZONA 6 AGENTE DE...
    fila_inicio = Column(Integer, nullable=False)               # fila Excel donde empieza el bloque
    fila_fin = Column(Integer, nullable=False)                  # fila Excel donde acaba el bloque

    agentes = relationship("Agente", back_populates="zona")


class Servicio(Base):
    __tablename__ = "servicios"
    codigo = Column(String(10), primary_key=True)     # 1, 2, 3F, D, E, VC...
    descripcion = Column(String(200), nullable=True)
    cambiable = Column(Boolean, default=False)


# ------------------------------------------------------------------
# AGENTES Y SESIONES
# ------------------------------------------------------------------

class Agente(Base):
    __tablename__ = "agentes"
    id = Column(Integer, primary_key=True)
    num_agente = Column(String(20), unique=True, nullable=False)   # col D
    nombre = Column(String(200), nullable=False)                    # col E
    zona_id = Column(Integer, ForeignKey("zonas.id"), nullable=False)
    fila_excel = Column(Integer, nullable=False)                    # fila exacta en Excel
    activo = Column(Boolean, default=True)
    pin_hash = Column(String(200), nullable=True)                   # hash del PIN
    debe_cambiar_pin = Column(Boolean, default=False)               # forzar cambio al primer login

    zona = relationship("Zona", back_populates="agentes")
    servicios = relationship("Cuadrante", back_populates="agente")


class Sesion(Base):
    __tablename__ = "sesiones"
    id = Column(Integer, primary_key=True)
    token = Column(String(64), unique=True, nullable=False, index=True)
    agente_id = Column(Integer, ForeignKey("agentes.id"), nullable=False)
    expira = Column(DateTime, nullable=False)
    creada = Column(DateTime, default=datetime.utcnow)

    agente = relationship("Agente")


# ------------------------------------------------------------------
# CUADRANTE
# ------------------------------------------------------------------

class Cuadrante(Base):
    __tablename__ = "cuadrante"
    id = Column(Integer, primary_key=True)
    agente_id = Column(Integer, ForeignKey("agentes.id"), nullable=False)
    mes = Column(Integer, nullable=False)             # 5 = mayo
    anio = Column(Integer, nullable=False)            # 2026
    dia = Column(Integer, nullable=False)             # 1..31
    servicio = Column(String(10), nullable=True)      # valor celda F, H, J...
    col_excel = Column(Integer, nullable=False)       # 6, 8, 10... (columna real)

    agente = relationship("Agente", back_populates="servicios")

    __table_args__ = (
        UniqueConstraint("agente_id", "mes", "anio", "dia", name="uq_cuadrante_agente_dia"),
    )


# ------------------------------------------------------------------
# RESTRICCIONES Y BLOQUEOS
# ------------------------------------------------------------------

class Restriccion(Base):
    __tablename__ = "restricciones"
    id = Column(Integer, primary_key=True)
    servicio_origen = Column(String(10), nullable=False)   # ej: "1"
    servicio_destino = Column(String(10), nullable=False)  # ej: "2"
    motivo = Column(String(200), nullable=True)            # "descanso mínimo"

    __table_args__ = (
        UniqueConstraint("servicio_origen", "servicio_destino", name="uq_restriccion"),
    )


class DiaBloqueado(Base):
    __tablename__ = "dias_bloqueados"
    id = Column(Integer, primary_key=True)
    agente_id = Column(Integer, ForeignKey("agentes.id"), nullable=True)   # NULL = bloqueo de zona
    zona_id = Column(Integer, ForeignKey("zonas.id"), nullable=True)       # NULL = bloqueo de agente
    fecha = Column(Date, nullable=False)
    motivo = Column(String(200), nullable=True)                            # FO, VC, huelga...


# ------------------------------------------------------------------
# SOLICITUDES Y CAMBIOS
# ------------------------------------------------------------------

class Solicitud(Base):
    __tablename__ = "solicitudes"
    id = Column(Integer, primary_key=True)
    solicitante_id = Column(Integer, ForeignKey("agentes.id"), nullable=False)
    companero_id = Column(Integer, ForeignKey("agentes.id"), nullable=False)
    dia_solicitante = Column(Integer, nullable=False)
    dia_companero = Column(Integer, nullable=False)
    servicio_solicitante = Column(String(10), nullable=False)
    servicio_companero = Column(String(10), nullable=False)
    estado = Column(String(20), default="pendiente")   # pendiente/aprobada/rechazada
    motivo_rechazo = Column(Text, nullable=True)
    fecha_solicitud = Column(DateTime, default=datetime.utcnow)
    fecha_resolucion = Column(DateTime, nullable=True)
    mes = Column(Integer, nullable=False)
    anio = Column(Integer, nullable=False)


class CambioAplicado(Base):
    __tablename__ = "cambios_aplicados"
    id = Column(Integer, primary_key=True)
    solicitud_id = Column(Integer, ForeignKey("solicitudes.id"), nullable=False)
    fecha_aplicacion = Column(DateTime, default=datetime.utcnow)
    volcado_excel = Column(Boolean, default=False)
    fecha_volcado = Column(DateTime, nullable=True)
# ------------------------------------------------------------------
# ADMINISTRACIÓN
# ------------------------------------------------------------------

class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True)
    usuario = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    nombre = Column(String(200), nullable=False)
    activo = Column(Boolean, default=True)


class SesionAdmin(Base):
    __tablename__ = "sesiones_admin"
    id = Column(Integer, primary_key=True)
    token = Column(String(64), unique=True, nullable=False, index=True)
    admin_id = Column(Integer, ForeignKey("admins.id"), nullable=False)
    expira = Column(DateTime, nullable=False)
    creada = Column(DateTime, default=datetime.utcnow)

    admin = relationship("Admin")
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