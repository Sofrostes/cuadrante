"""
Acceso a la tabla clave-valor Configuracion + helpers de layout/ruta.
"""

from pathlib import Path

from app.db.modelos import Configuracion
from app.servicios.layout_excel import LayoutExcel


K_RUTA = "excel.ruta"
K_HOJA = "excel.hoja"
K_FILA_INI = "excel.fila_inicio_datos"
K_COL_ID = "excel.col_identificador"
K_COL_NOMBRE = "excel.col_nombre"
K_COL_CF = "excel.col_cf"
K_COL_SERVICIOS = "excel.col_servicios"
K_GAP = "excel.gap"
K_ULT_MSG = "excel.ultima_prueba_msg"
K_ULT_OK = "excel.ultima_prueba_ok"

DESCRIPCIONES = {
    K_RUTA: "Ruta completa al Excel maestro (.xlsx/.xlsm)",
    K_HOJA: "Hoja del Excel a tratar",
    K_FILA_INI: "Primera fila con datos (1-based)",
    K_COL_ID: "Columna del identificador de grupo (AE6)",
    K_COL_NOMBRE: "Columna del nombre del trabajador",
    K_COL_CF: "Columna del carnet ferroviario",
    K_COL_SERVICIOS: "Columna del primer servicio/día",
    K_GAP: "Columnas vacías entre servicios (1 = se salta 1)",
    K_ULT_MSG: "Resultado de la última prueba",
    K_ULT_OK: "1 si la última prueba fue OK",
}


def get_config(db, clave, default=None):
    fila = db.get(Configuracion, clave)
    return fila.valor if fila and fila.valor is not None else default


def set_config(db, clave, valor):
    fila = db.get(Configuracion, clave)
    if fila is None:
        fila = Configuracion(
            clave=clave, valor=valor, descripcion=DESCRIPCIONES.get(clave)
        )
        db.add(fila)
    else:
        fila.valor = valor
    db.commit()


def get_all_config(db):
    return {f.clave: f.valor for f in db.query(Configuracion).all()}


def get_layout(db) -> LayoutExcel:
    return LayoutExcel(
        col_identificador=(get_config(db, K_COL_ID, "A") or "A"),
        col_nombre=(get_config(db, K_COL_NOMBRE, "B") or "B"),
        col_cf=(get_config(db, K_COL_CF, "C") or "C"),
        fila_inicio_datos=int(get_config(db, K_FILA_INI, "2") or "2"),
        col_servicios=(get_config(db, K_COL_SERVICIOS, "E") or "E"),
        gap=int(get_config(db, K_GAP, "1") or "1"),
    )


def get_ruta_excel(db) -> Path:
    ruta = (get_config(db, K_RUTA, "") or "").strip()
    if not ruta:
        raise RuntimeError(
            "Configura 'excel.ruta' en /admin/configuracion"
        )
    return Path(ruta)


def get_hoja(db) -> str:
    return (get_config(db, K_HOJA, "") or "").strip()