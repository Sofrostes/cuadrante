"""
Volcado real de cambios aprobados a la hoja MAYO 2026 del Excel.

Motor: xlwings (Excel real vía COM). Preserva todo el libro tal cual:
enlaces, gráficos, estilos, fórmulas, formato condicional, etc.

Requisitos:
    pip install xlwings
    Excel instalado en la máquina.
"""

import os
import shutil
from pathlib import Path

import xlwings as xw

from app.db.modelos import Agente, Cuadrante

RUTA_EXCEL = Path("datos") / "mayo2026.xlsx"
RUTA_BAK   = Path("datos") / "mayo2026_backup.xlsx"
HOJA_MES   = "MAYO 2026"


def _leer_datos_para_cambio(db, solicitud):
    """
    Devuelve (fila_sol, col_sol, fila_comp, col_comp) o None si falta algo.
    """
    ag_sol = db.query(Agente).filter_by(id=solicitud.solicitante_id).first()
    ag_comp = db.query(Agente).filter_by(id=solicitud.companero_id).first()
    if not ag_sol or not ag_comp:
        return None

    reg_sol = db.query(Cuadrante).filter_by(
        agente_id=ag_sol.id,
        mes=solicitud.mes,
        anio=solicitud.anio,
        dia=solicitud.dia_solicitante,
    ).first()
    reg_comp = db.query(Cuadrante).filter_by(
        agente_id=ag_comp.id,
        mes=solicitud.mes,
        anio=solicitud.anio,
        dia=solicitud.dia_companero,
    ).first()

    if not reg_sol or not reg_comp:
        return None

    return (
        ag_sol.fila_excel, reg_sol.col_excel,
        ag_comp.fila_excel, reg_comp.col_excel,
    )


def _borrar_silencioso(ruta: Path):
    try:
        if ruta.exists():
            ruta.unlink()
    except Exception:
        pass


def volcar_a_excel(db, cambios):
    """
    cambios: lista de tuplas (CambioAplicado, Solicitud)
    Devuelve (ids_ok, errores)
    """
    if not cambios:
        return [], []

    ruta_excel_abs = RUTA_EXCEL.resolve()

    if not ruta_excel_abs.exists():
        return [], [f"No existe el fichero {ruta_excel_abs}"]

    # 1) Backup la primera vez
    if not RUTA_BAK.exists():
        try:
            shutil.copy2(ruta_excel_abs, RUTA_BAK)
        except Exception as e:
            return [], [f"No se pudo crear el backup {RUTA_BAK}: {e}"]

    ids_ok = []
    errores = []

    app = None
    wb = None
    try:
        # 2) Abrir Excel en segundo plano
        app = xw.App(visible=False, add_book=False)
        app.display_alerts = False
        app.screen_updating = False

        wb = app.books.open(str(ruta_excel_abs))

        # 3) Localizar hoja
        nombres = [s.name for s in wb.sheets]
        if HOJA_MES not in nombres:
            return [], [f"La hoja '{HOJA_MES}' no existe. Hojas: {nombres}"]

        hoja = wb.sheets[HOJA_MES]

        # 4) Escribir cambios
        for cambio, solicitud in cambios:
            try:
                datos = _leer_datos_para_cambio(db, solicitud)
                if not datos:
                    errores.append(
                        f"Solicitud {solicitud.id}: faltan datos de agente/cuadrante"
                    )
                    continue

                fila_sol, col_sol, fila_comp, col_comp = datos

                # xlwings usa .range(fila, columna) con 1-based, igual que Excel
                hoja.range((fila_sol, col_sol)).value = solicitud.servicio_companero
                hoja.range((fila_comp, col_comp)).value = solicitud.servicio_solicitante

                ids_ok.append(cambio.id)
            except Exception as e:
                errores.append(f"Cambio {cambio.id} (solicitud {solicitud.id}): {e}")

        # 5) Guardar solo si algo se ha escrito
        if ids_ok:
            wb.save()

    except Exception as e:
        errores.append(f"Error con Excel: {e}")
        return [], errores
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

    return ids_ok, errores