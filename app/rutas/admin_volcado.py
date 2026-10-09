"""
Volcado a Excel desde el panel admin.
Como no tienes un modelo 'Registro', el endpoint /forzar recibe las
claves a volcar y delega en tu función real de armado.

Adapta `_iter_pendientes_desde_bd(db)` a tu modelo real.
"""

from datetime import date

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.modelos.volcado_estado import VolcadoEstado
from app.servicios import configuracion as cfg
from app.servicios.volcado_service import volcar, pendientes
from app.servicios.bloqueos import comprobar_rango, MENSAJE_BLOQUEO


router = APIRouter(prefix="/admin/volcado", tags=["admin"])


def _iter_pendientes_desde_bd(db: Session):
    """
    TODO: sustituir por tu lógica real.
    Debe devolver iterables de (clave: str, fila_excel: int, turnos: list).

    Ejemplo:
        for t in db.query(Turno).filter(...).all():
            yield (str(t.id), t.fila_excel, [t.d1, t.d2, ...])
    """
    # Placeholder: no devuelve nada hasta que lo adaptes.
    return iter(())


@router.get("/pendientes")
def ver_pendientes(db: Session = Depends(get_db)):
    regs = pendientes(db)
    return {"total": len(regs), "claves": [r.clave for r in regs]}


@router.post("/forzar")
def forzar(db: Session = Depends(get_db)):
    try:
        ruta = cfg.get_ruta_excel(db)
        hoja = cfg.get_hoja(db)
        layout = cfg.get_layout(db)
    except Exception as e:
        return JSONResponse(
            {"ok": False, "mensaje": f"Config incompleta: {e}"}, status_code=400
        )

    if not hoja:
        return JSONResponse(
            {"ok": False, "mensaje": "Falta configurar la hoja"}, status_code=400
        )

    try:
        reporte = volcar(db, ruta, hoja, layout, lambda: _iter_pendientes_desde_bd(db))
    except Exception as e:
        return JSONResponse(
            {"ok": False, "mensaje": f"Error en volcado: {e}"}, status_code=500
        )
    return JSONResponse(reporte)


# --------- Bloqueos: endpoints para gestionar desde el panel ---------

@router.post("/bloqueos/crear")
def crear_bloqueo(
    fecha: date,
    motivo: str = "",
    grupo: str | None = None,
    db: Session = Depends(get_db),
):
    from app.modelos.bloqueo import BloqueoDia

    b = BloqueoDia(fecha=fecha, motivo=motivo or None, grupo=grupo or None)
    db.add(b)
    db.commit()
    return {"ok": True, "id": b.id}


@router.get("/bloqueos/listar")
def listar_bloqueos(db: Session = Depends(get_db)):
    from app.modelos.bloqueo import BloqueoDia

    items = db.query(BloqueoDia).order_by(BloqueoDia.fecha).all()
    return {
        "total": len(items),
        "items": [
            {
                "id": b.id,
                "fecha": b.fecha.isoformat(),
                "motivo": b.motivo,
                "grupo": b.grupo,
            }
            for b in items
        ],
    }


@router.post("/bloqueos/eliminar/{bloqueo_id}")
def eliminar_bloqueo(bloqueo_id: int, db: Session = Depends(get_db)):
    from app.modelos.bloqueo import BloqueoDia

    b = db.get(BloqueoDia, bloqueo_id)
    if not b:
        return JSONResponse({"ok": False, "mensaje": "No existe"}, status_code=404)
    db.delete(b)
    db.commit()
    return {"ok": True}


@router.get("/bloqueos/comprobar")
def comprobar(
    fecha: date,
    grupo: str | None = None,
    db: Session = Depends(get_db),
):
    res = comprobar_rango(db, [fecha], grupo)
    return {
        "bloqueado": bool(res),
        "mensaje": MENSAJE_BLOQUEO if res else None,
        "bloqueos": res,
    }