"""
Servicio de volcado a Excel. NO resuelve rutas: las recibe ya resueltas
para que sea testeable y para poder reutilizarlo desde CLI o desde API.
"""

from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.modelos.registro import Registro
from app.servicios.layout_excel import LayoutExcel


def registros_pendientes(db: Session) -> list[Registro]:
    """Registros que NO se han volcado con éxito (nunca intentados o fallidos)."""
    return (
        db.query(Registro)
        .filter(Registro.volcado_ok.is_(False))
        .order_by(Registro.id)
        .all()
    )


def volcar(
    db: Session,
    ruta_excel: Path,
    hoja: str,
    layout: LayoutExcel,
    solo_pendientes: bool = True,
) -> dict:
    """
    Vuelca a Excel los registros pendientes.
    Devuelve un reporte con éxito/fallo por registro.
    """
    import xlwings as xw

    pendientes = registros_pendientes(db) if solo_pendientes else db.query(Registro).all()

    reporte = {
        "total": len(pendientes),
        "ok": 0,
        "fallo": 0,
        "detalles": [],  # [{id, ok, mensaje}]
    }

    if not pendientes:
        return reporte

    app = None
    wb = None
    try:
        app = xw.App(visible=False, add_book=False)
        app.display_alerts = False
        app.screen_updating = False
        wb = app.books.open(str(ruta_excel), update_links=False, read_only=False)
        hoja_obj = wb.sheets[hoja]

        for reg in pendientes:
            try:
                fila = reg.fila_excel  # <- ajusta: ¿cómo sabes en qué fila va cada uno?
                for i, turno in enumerate(reg.turnos):  # ajusta a tu modelo real
                    col = layout.columna_servicio(i)
                    hoja_obj.range(f"{col}{fila}").value = turno

                reg.volcado_ok = True
                reg.volcado_error = None
                reg.volcado_intento_en = datetime.utcnow()
                db.commit()

                reporte["ok"] += 1
                reporte["detalles"].append(
                    {"id": reg.id, "ok": True, "mensaje": f"Volcado en fila {fila}"}
                )
            except Exception as e:
                db.rollback()
                # Dejamos el registro como pendiente para reintento
                reg.volcado_ok = False
                reg.volcado_error = f"{type(e).__name__}: {e}"
                reg.volcado_intento_en = datetime.utcnow()
                db.add(reg)
                db.commit()

                reporte["fallo"] += 1
                reporte["detalles"].append(
                    {"id": reg.id, "ok": False, "mensaje": reg.volcado_error}
                )
    finally:
        try:
            if wb is not None:
                wb.close()
        except Exception:
            pass
        try:
            if app is not None:
                app.quit()
        except Exception:
            pass

    return reporte