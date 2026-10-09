from datetime import date
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db import get_db
from app.servicios.restricciones import evaluar_tramo, turno_de


router = APIRouter(prefix="/consola", tags=["consola"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def ver(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("consola/index.html", {"request": request})


@router.get("/evaluar")
def evaluar(
    trabajador_id: int,
    grupo: str | None = None,
    fecha: date = Query(..., description="Día actual del cambio"),
    turno_solicitado: str = Query(...),
    db: Session = Depends(get_db),
):
    """Vista previa para la consola antes de aceptar un cambio."""
    fecha_posterior = date.fromordinal(fecha.toordinal() + 1)

    return {
        "fecha_actual": fecha.isoformat(),
        "fecha_posterior": fecha_posterior.isoformat(),
        "turno_actual_previo": turno_de(db, trabajador_id, fecha),
        "turno_dia_posterior": turno_de(db, trabajador_id, fecha_posterior),
        "evaluacion": evaluar_tramo(
            db,
            trabajador_id=trabajador_id,
            grupo=grupo,
            fecha_actual=fecha,
            fecha_posterior=fecha_posterior,
            turno_solicitado=turno_solicitado,
        ),
    }