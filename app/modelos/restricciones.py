from datetime import date
from sqlalchemy.orm import Session

from app.modelos.regla_turno import ReglaIncompatibilidad
from app.servicios.bloqueos import comprobar_rango


def turno_de(db: Session, trabajador_id: int, fecha: date) -> str | None:
    """Devuelve el turno del trabajador ese día, o None si no tiene."""
    # AJUSTA a tu modelo real de turnos asignados
    from app.modelos.turno_asignado import TurnoAsignado  # ejemplo
    t = (
        db.query(TurnoAsignado)
        .filter(
            TurnoAsignado.trabajador_id == trabajador_id,
            TurnoAsignado.fecha == fecha,
        )
        .first()
    )
    return t.turno if t else None


def evaluar_tramo(
    db: Session,
    trabajador_id: int,
    grupo: str | None,
    fecha_actual: date,
    fecha_posterior: date,
    turno_solicitado: str,
) -> dict:
    """
    Evalúa una solicitud de cambio que afecta a fecha_actual (día D).
    Comprueba:
      - Bloqueos activos en D o D+1 -> mensaje "Habla con el gestor..."
      - Incompatibilidad entre turno de D-1 / turno solicitado en D
      - Incompatibilidad entre turno solicitado en D / turno de D+1
    """
    resultado = {
        "ok": True,
        "avisos": [],
        "incompatibilidades": [],
        "bloqueos": [],
    }

    # 1) Bloqueos activos
    bloqueos = comprobar_rango(db, [fecha_actual, fecha_posterior], grupo=grupo)
    if bloqueos:
        resultado["ok"] = False
        resultado["bloqueos"] = bloqueos
        resultado["mensaje"] = bloqueos[0]["mensaje"]
        return resultado

    # 2) Incompatibilidad con día anterior
    turno_prev = turno_de(db, trabajador_id, date.fromordinal(fecha_actual.toordinal() - 1))
    if turno_prev:
        regla = _busca_regla(db, turno_prev, turno_solicitado)
        if regla:
            resultado["ok"] = False
            resultado["incompatibilidades"].append(
                {
                    "tipo": "con_dia_anterior",
                    "turno_previo": turno_prev,
                    "turno_nuevo": turno_solicitado,
                    "motivo": regla.motivo,
                }
            )

    # 3) Incompatibilidad con día posterior
    turno_post = turno_de(db, trabajador_id, fecha_posterior)
    if turno_post:
        regla = _busca_regla(db, turno_solicitado, turno_post)
        if regla:
            resultado["ok"] = False
            resultado["incompatibilidades"].append(
                {
                    "tipo": "con_dia_posterior",
                    "turno_previo": turno_solicitado,
                    "turno_nuevo": turno_post,
                    "motivo": regla.motivo,
                }
            )

    return resultado


def _busca_regla(db: Session, a: str, b: str) -> ReglaIncompatibilidad | None:
    return (
        db.query(ReglaIncompatibilidad)
        .filter(
            ReglaIncompatibilidad.activa.is_(True),
            ReglaIncompatibilidad.turno_a == a,
            ReglaIncompatibilidad.turno_b == b,
        )
        .first()
    )