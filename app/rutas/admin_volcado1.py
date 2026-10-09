from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.servicios import configuracion as cfg
from app.servicios.volcado_service import volcar, registros_pendientes


router = APIRouter(prefix="/admin/volcado", tags=["admin"])


@router.get("/pendientes")
def pendientes(db: Session = Depends(get_db)):
    regs = registros_pendientes(db)
    return {
        "total": len(regs),
        "ids": [r.id for r in regs],
    }


@router.post("/forzar")
def forzar(db: Session = Depends(get_db)):
    """
    Vuelca SOLO los registros pendientes (nunca volcados o con fallo).
    Los que fallan quedan como pendientes para el siguiente intento.
    """
    try:
        ruta = cfg.get_ruta_excel(db)
        hoja = cfg.get_config(db, cfg.K_HOJA) or ""
        layout = cfg.get_layout(db)
    except Exception as e:
        return JSONResponse(
            {"ok": False, "mensaje": f"Config incompleta: {e}"}, status_code=400
        )

    reporte = volcar(db, ruta, hoja, layout, solo_pendientes=True)
    reporte["ok_global"] = reporte["fallo"] == 0 and reporte["total"] > 0
    return JSONResponse(reporte)