"""
Endpoints de /admin/configuracion.
Ajusta el Depends de auth a tu sistema real.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db import get_db
from app.servicios import configuracion as cfg
from app.servicios import rutas_windows as rw
from app.servicios.excel_prueba import probar_excel, cargar_nombres_hojas
from app.servicios.layout_excel import LayoutExcel


router = APIRouter(prefix="/admin/configuracion", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")


def _construir_layout(
    col_id: str, col_nombre: str, col_cf: str,
    fila_ini: int, col_serv: str, gap: int,
) -> LayoutExcel:
    return LayoutExcel(
        col_identificador=(col_id or "A").strip().upper(),
        col_nombre=(col_nombre or "B").strip().upper(),
        col_cf=(col_cf or "C").strip().upper(),
        fila_inicio_datos=int(fila_ini or 2),
        col_servicios=(col_serv or "E").strip().upper(),
        gap=int(gap or 0),
    )


@router.get("", response_class=HTMLResponse)
def ver(request: Request, db: Session = Depends(get_db)):
    datos = cfg.get_all_config(db)
    return templates.TemplateResponse(
        "admin/configuracion.html",
        {
            "request": request,
            "datos": datos,
            "diag": rw.diagnostico(),
        },
    )


@router.post("/guardar")
def guardar(
    excel_ruta: str = Form(""),
    excel_hoja: str = Form(""),
    col_identificador: str = Form("A"),
    col_nombre: str = Form("B"),
    col_cf: str = Form("C"),
    fila_inicio_datos: int = Form(2),
    col_servicios: str = Form("E"),
    gap: int = Form(1),
    db: Session = Depends(get_db),
):
    try:
        layout = _construir_layout(
            col_identificador, col_nombre, col_cf,
            fila_inicio_datos, col_servicios, gap,
        )
    except Exception as e:
        return JSONResponse(
            {"ok": False, "mensaje": f"Layout inválido: {e}"}, status_code=400
        )

    ruta_norm = rw.normalizar_ruta(excel_ruta) if excel_ruta else ""

    cfg.set_config(db, cfg.K_RUTA, ruta_norm)
    cfg.set_config(db, cfg.K_HOJA, excel_hoja.strip())
    cfg.set_config(db, cfg.K_COL_ID, layout.col_identificador)
    cfg.set_config(db, cfg.K_COL_NOMBRE, layout.col_nombre)
    cfg.set_config(db, cfg.K_COL_CF, layout.col_cf)
    cfg.set_config(db, cfg.K_FILA_INI, str(layout.fila_inicio_datos))
    cfg.set_config(db, cfg.K_COL_SERVICIOS, layout.col_servicios)
    cfg.set_config(db, cfg.K_GAP, str(layout.gap))

    return JSONResponse(
        {"ok": True, "ruta_normalizada": ruta_norm, "mensaje": "Configuración guardada"}
    )


@router.post("/cargar-hojas")
def cargar_hojas(
    excel_ruta: str = Form(""),
):
    ruta_norm = rw.normalizar_ruta(excel_ruta) if excel_ruta else ""
    if not ruta_norm:
        return JSONResponse(
            {"ok": False, "mensaje": "Falta la ruta", "hojas": []},
            status_code=400,
        )
    ruta_completa = Path(ruta_norm)
    res = cargar_nombres_hojas(ruta_completa)
    res["ruta_normalizada"] = ruta_norm
    res["ruta_completa"] = str(ruta_completa)
    return JSONResponse(res)


@router.post("/preview-layout")
def preview_layout(
    col_inicio_servicios: str = Form("E"),
    gap: int = Form(1),
    fila_inicio_datos: int = Form(2),
    col_identificador: str = Form("A"),
    col_nombre: str = Form("B"),
    col_cf: str = Form("C"),
    n: int = Form(10),
):
    try:
        layout = _construir_layout(
            col_identificador, col_nombre, col_cf,
            fila_inicio_datos, col_inicio_servicios, gap,
        )
    except Exception as e:
        return JSONResponse(
            {"ok": False, "mensaje": f"Layout inválido: {e}"}, status_code=400
        )
    return JSONResponse(
        {
            "ok": True,
            "columnas": layout.primeros_servicios(n),
            "primera_celda": layout.celda_servicio(0),
        }
    )


@router.post("/probar")
def probar(
    excel_ruta: str = Form(""),
    excel_hoja: str = Form(""),
    col_identificador: str = Form("A"),
    col_nombre: str = Form("B"),
    col_cf: str = Form("C"),
    fila_inicio_datos: int = Form(2),
    col_servicios: str = Form("E"),
    gap: int = Form(1),
    db: Session = Depends(get_db),
):
    try:
        layout = _construir_layout(
            col_identificador, col_nombre, col_cf,
            fila_inicio_datos, col_servicios, gap,
        )
    except Exception as e:
        return JSONResponse(
            {"ok": False, "mensaje": f"Layout inválido: {e}"}, status_code=400
        )

    ruta_norm = rw.normalizar_ruta(excel_ruta) if excel_ruta else ""
    if not ruta_norm:
        return JSONResponse(
            {"ok": False, "mensaje": "Falta la ruta"}, status_code=400
        )

    ruta_completa = Path(ruta_norm)
    res = probar_excel(ruta_completa, excel_hoja or None, layout)
    res["ruta_normalizada"] = ruta_norm
    res["ruta_completa"] = str(ruta_completa)

    cfg.set_config(db, cfg.K_ULT_MSG, res["mensaje"])
    cfg.set_config(db, cfg.K_ULT_OK, "1" if res["ok"] else "0")
    return JSONResponse(res)


@router.get("/diagnostico")
def diagnostico():
    return JSONResponse(rw.diagnostico())