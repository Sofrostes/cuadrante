"""
Pruebas de lectura/escritura del Excel maestro con xlwings.
Nunca lo abras desde un GET normal: esto arranca Excel COM.
"""

import threading
import uuid
from pathlib import Path

import xlwings as xw

from app.servicios.layout_excel import LayoutExcel


_LOCK = threading.Lock()

# Celda "lejana" para prueba general de escritura. Si sospechas de .xls
# antiguo, cambia por algo tipo 'ZZ10000'.
_CELDA_CONTROL = "XFD1048576"


def probar_excel(
    ruta: str | Path,
    hoja: str | None = None,
    layout: LayoutExcel | None = None,
    muestra_turnos: int = 5,
) -> dict:
    layout = layout or LayoutExcel()
    res = {
        "ok": False,
        "mensaje": "",
        "hojas": [],
        "hoja_probada": None,
        "escritura_control_ok": False,
        "escritura_servicio_ok": False,
        "celda_servicio_probada": None,
        "muestra": [],
        "detalle_error": None,
    }

    p = Path(ruta)
    if not p.exists():
        res["mensaje"] = f"No existe la ruta: {p}"
        return res
    if not p.is_file():
        res["mensaje"] = f"La ruta no es un fichero: {p}"
        return res

    with _LOCK:
        app = None
        wb = None
        try:
            app = xw.App(visible=False, add_book=False)
            app.display_alerts = False
            app.screen_updating = False

            wb = app.books.open(str(p), update_links=False, read_only=False)

            hojas = [s.name for s in wb.sheets]
            res["hojas"] = hojas
            if not hojas:
                res["mensaje"] = "El libro no tiene hojas"
                return res

            if hoja and hoja in hojas:
                hoja_obj = wb.sheets[hoja]
            else:
                hoja_obj = wb.sheets[0]
                if hoja:
                    res["mensaje"] = (
                        f"Hoja '{hoja}' no existe; probando con '{hoja_obj.name}'. "
                    )
            res["hoja_probada"] = hoja_obj.name

            # A) Escritura de control
            celda_ctrl = hoja_obj.range(_CELDA_CONTROL)
            previo_ctrl = celda_ctrl.value
            marca = f"__probe_{uuid.uuid4().hex[:8]}__"
            celda_ctrl.value = marca
            res["escritura_control_ok"] = celda_ctrl.value == marca
            celda_ctrl.value = previo_ctrl

            # B) Escritura en primera celda de servicio
            celda_serv = layout.celda_servicio(0)
            res["celda_servicio_probada"] = f"{hoja_obj.name}!{celda_serv}"
            r = hoja_obj.range(celda_serv)
            previo_s = r.value
            r.value = marca
            res["escritura_servicio_ok"] = r.value == marca
            r.value = previo_s

            # C) Lectura de muestra
            muestra = []
            for i in range(muestra_turnos):
                col = layout.columna_servicio(i)
                celda = f"{col}{layout.fila_inicio_datos}"
                try:
                    v = hoja_obj.range(celda).value
                except Exception:
                    v = "<err>"
                muestra.append(f"{celda}={v!r}")
            res["muestra"] = muestra

            res["ok"] = res["escritura_control_ok"] and res["escritura_servicio_ok"]
            prefijo = res["mensaje"]
            if res["ok"]:
                res["mensaje"] = (
                    f"{prefijo}OK · {len(hojas)} hojas · "
                    f"escritura OK en {res['celda_servicio_probada']}"
                )
            else:
                res["mensaje"] = (
                    f"{prefijo}El archivo se abrió pero falló la escritura "
                    f"(control={res['escritura_control_ok']}, "
                    f"servicio={res['escritura_servicio_ok']}). "
                    "¿Está abierto por otro usuario?"
                )
        except Exception as e:
            res["detalle_error"] = f"{type(e).__name__}: {e}"
            res["mensaje"] = f"Error abriendo/probando Excel: {e}"
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

    return res


def cargar_nombres_hojas(ruta: str | Path) -> dict:
    p = Path(ruta)
    if not p.exists() or not p.is_file():
        return {"ok": False, "mensaje": f"No existe: {p}", "hojas": []}

    with _LOCK:
        app = None
        wb = None
        try:
            app = xw.App(visible=False, add_book=False)
            app.display_alerts = False
            app.screen_updating = False
            wb = app.books.open(str(p), update_links=False, read_only=True)
            hojas = [s.name for s in wb.sheets]
            return {"ok": True, "mensaje": f"{len(hojas)} hojas", "hojas": hojas}
        except Exception as e:
            return {"ok": False, "mensaje": f"{type(e).__name__}: {e}", "hojas": []}
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