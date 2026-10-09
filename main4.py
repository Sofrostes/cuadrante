import secrets
import bcrypt
from datetime import datetime, timedelta

from fastapi import FastAPI, Request, HTTPException, Form, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.db.conexion import crear_tablas, SessionLocal
from app.db.modelos import Zona, Agente, Cuadrante, Sesion, Servicio, DiaBloqueado, Restriccion, Solicitud, CambioAplicado

# ------------------------------------------------------------------
# CONFIGURACIÓN
# ------------------------------------------------------------------

PIN_INICIAL = "1234"
DURACION_SESION_HORAS = 8

app = FastAPI(title="Cuadrantes")
templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
def al_arrancar():
    crear_tablas()
    print("✅ Base de datos lista")


# ------------------------------------------------------------------
# HELPERS DE SESIÓN
# ------------------------------------------------------------------

def crear_sesion(db, agente: Agente) -> str:
    token = secrets.token_urlsafe(32)
    expira = datetime.utcnow() + timedelta(hours=DURACION_SESION_HORAS)
    db.add(Sesion(token=token, agente_id=agente.id, expira=expira))
    db.commit()
    return token


def agente_de_sesion(db, token: str | None) -> Agente | None:
    if not token:
        return None
    sesion = db.query(Sesion).filter_by(token=token).first()
    if not sesion:
        return None
    if sesion.expira < datetime.utcnow():
        db.delete(sesion)
        db.commit()
        return None
    return db.query(Agente).filter_by(id=sesion.agente_id).first()


def cerrar_sesion(db, token: str | None):
    if not token:
        return
    sesion = db.query(Sesion).filter_by(token=token).first()
    if sesion:
        db.delete(sesion)
        db.commit()


# ------------------------------------------------------------------
# LOGIN / LOGOUT
# ------------------------------------------------------------------

@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request, error: str | None = None):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": error},
    )


@app.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    num_agente: str = Form(...),
    pin: str = Form(...),
):
    db = SessionLocal()
    try:
        agente = db.query(Agente).filter_by(num_agente=num_agente.strip()).first()
        if not agente or not agente.activo:
            return RedirectResponse("/login?error=Agente+no+encontrado", status_code=303)

        if not agente.pin_hash:
            agente.pin_hash = bcrypt.hashpw(pin.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            agente.debe_cambiar_pin = (pin == PIN_INICIAL)
            db.commit()
        else:
            if not bcrypt.checkpw(pin.encode("utf-8"), agente.pin_hash.encode("utf-8")):
                return RedirectResponse("/login?error=PIN+incorrecto", status_code=303)

        token = crear_sesion(db, agente)

        destino = "/cambiar-pin" if agente.debe_cambiar_pin else "/"
        respuesta = RedirectResponse(destino, status_code=303)
        respuesta.set_cookie(
            key="sesion",
            value=token,
            httponly=True,
            max_age=DURACION_SESION_HORAS * 3600,
            samesite="lax",
        )
        return respuesta
    finally:
        db.close()


@app.get("/logout")
def logout(request: Request, sesion: str | None = Cookie(default=None)):
    db = SessionLocal()
    try:
        cerrar_sesion(db, sesion)
    finally:
        db.close()
    respuesta = RedirectResponse("/login", status_code=303)
    respuesta.delete_cookie("sesion")
    return respuesta


# ------------------------------------------------------------------
# CAMBIO DE PIN
# ------------------------------------------------------------------

@app.get("/cambiar-pin", response_class=HTMLResponse)
def cambiar_pin_form(
    request: Request,
    sesion: str | None = Cookie(default=None),
    error: str | None = None,
):
    db = SessionLocal()
    try:
        agente = agente_de_sesion(db, sesion)
        if not agente:
            return RedirectResponse("/login", status_code=303)
        return templates.TemplateResponse(
            request=request,
            name="cambiar_pin.html",
            context={"agente": agente, "error": error},
        )
    finally:
        db.close()


@app.post("/cambiar-pin", response_class=HTMLResponse)
def cambiar_pin(
    request: Request,
    pin_actual: str = Form(...),
    pin_nuevo: str = Form(...),
    pin_repetir: str = Form(...),
    sesion: str | None = Cookie(default=None),
):
    db = SessionLocal()
    try:
        agente = agente_de_sesion(db, sesion)
        if not agente:
            return RedirectResponse("/login", status_code=303)

        if not bcrypt.checkpw(pin_actual.encode("utf-8"), agente.pin_hash.encode("utf-8")):
            return RedirectResponse("/cambiar-pin?error=PIN+actual+incorrecto", status_code=303)

        if pin_nuevo != pin_repetir:
            return RedirectResponse("/cambiar-pin?error=Los+PIN+no+coinciden", status_code=303)

        if len(pin_nuevo) < 4:
            return RedirectResponse("/cambiar-pin?error=El+PIN+debe+tener+al+menos+4+caracteres", status_code=303)

        agente.pin_hash = bcrypt.hashpw(pin_nuevo.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        agente.debe_cambiar_pin = False
        db.commit()

        return RedirectResponse("/", status_code=303)
    finally:
        db.close()


# ------------------------------------------------------------------
# VISTAS PROTEGIDAS
# ------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def inicio(request: Request, sesion: str | None = Cookie(default=None)):
    db = SessionLocal()
    try:
        agente = agente_de_sesion(db, sesion)
        if not agente:
            return RedirectResponse("/login", status_code=303)
        if agente.debe_cambiar_pin:
            return RedirectResponse("/cambiar-pin", status_code=303)

        zonas = db.query(Zona).order_by(Zona.codigo).all()
        return templates.TemplateResponse(
            request=request,
            name="inicio.html",
            context={"agente": agente, "zonas": zonas},
        )
    finally:
        db.close()


@app.get("/zona/{codigo}", response_class=HTMLResponse)
def ver_zona(
    request: Request,
    codigo: str,
    mes: int = 5,
    anio: int = 2026,
    sesion: str | None = Cookie(default=None),
):
    db = SessionLocal()
    try:
        agente = agente_de_sesion(db, sesion)
        if not agente:
            return RedirectResponse("/login", status_code=303)
        if agente.debe_cambiar_pin:
            return RedirectResponse("/cambiar-pin", status_code=303)

        zona = db.query(Zona).filter_by(codigo=codigo.upper()).first()
        if not zona:
            raise HTTPException(404, f"Zona {codigo} no existe")

        agentes = (
            db.query(Agente)
            .filter_by(zona_id=zona.id, activo=True)
            .order_by(Agente.fila_excel)
            .all()
        )

        dias = list(range(1, 32))
        matriz = {ag.id: {d: "" for d in dias} for ag in agentes}

        if agentes:
            filas = (
                db.query(Cuadrante)
                .filter(
                    Cuadrante.mes == mes,
                    Cuadrante.anio == anio,
                    Cuadrante.agente_id.in_([a.id for a in agentes]),
                )
                .all()
            )
            for reg in filas:
                matriz[reg.agente_id][reg.dia] = reg.servicio or ""

        return templates.TemplateResponse(
            request=request,
            name="zona.html",
            context={
                "agente_logueado": agente,
                "zona": zona,
                "agentes": agentes,
                "dias": dias,
                "matriz": matriz,
                "mes": mes,
                "anio": anio,
            },
        )
    finally:
        db.close()


# ------------------------------------------------------------------
# SOLICITAR CAMBIO
# ------------------------------------------------------------------

@app.get("/solicitar-cambio", response_class=HTMLResponse)
def solicitar_cambio_form(
    request: Request,
    sesion: str | None = Cookie(default=None),
    error: str | None = None,
    ok: str | None = None,
):
    from datetime import date

    db = SessionLocal()
    try:
        agente = agente_de_sesion(db, sesion)
        if not agente:
            return RedirectResponse("/login", status_code=303)
        if agente.debe_cambiar_pin:
            return RedirectResponse("/cambiar-pin", status_code=303)

        hoy = date(2026, 5, 1)  # Fecha fija de pruebas

        companeros = (
            db.query(Agente)
            .filter(
                Agente.zona_id == agente.zona_id,
                Agente.activo == True,
                Agente.id != agente.id,
            )
            .order_by(Agente.fila_excel)
            .all()
        )

        mis_registros = (
            db.query(Cuadrante)
            .filter(
                Cuadrante.agente_id == agente.id,
                Cuadrante.mes == 5,
                Cuadrante.anio == 2026,
                Cuadrante.dia >= hoy.day,
            )
            .order_by(Cuadrante.dia)
            .all()
        )

        otros_ids = [c.id for c in companeros]
        cuadrante_companeros = (
            db.query(Cuadrante)
            .filter(
                Cuadrante.agente_id.in_(otros_ids),
                Cuadrante.mes == 5,
                Cuadrante.anio == 2026,
                Cuadrante.dia >= hoy.day,
            )
            .all()
            if otros_ids
            else []
        )

        matriz_companeros = {c.id: {} for c in companeros}
        for reg in cuadrante_companeros:
            matriz_companeros[reg.agente_id][reg.dia] = reg.servicio or ""

        servicios_cambiables = {
            s.codigo
            for s in db.query(Servicio).filter_by(cambiable=True).all()
        }

        return templates.TemplateResponse(
            request=request,
            name="solicitar_cambio.html",
            context={
                "agente": agente,
                "companeros": companeros,
                "mis_registros": mis_registros,
                "matriz_companeros": matriz_companeros,
                "servicios_cambiables": servicios_cambiables,
                "error": error,
                "ok": ok,
            },
        )
    finally:
        db.close()


@app.post("/solicitar-cambio", response_class=HTMLResponse)
def solicitar_cambio(
    request: Request,
    dia_solicitante: int = Form(...),
    companero_id: int = Form(...),
    dia_companero: int = Form(...),
    sesion: str | None = Cookie(default=None),
):
    from datetime import date
    from urllib.parse import quote

    def _error(msg: str):
        return RedirectResponse(f"/solicitar-cambio?error={quote(msg)}", status_code=303)

    db = SessionLocal()
    try:
        agente = agente_de_sesion(db, sesion)
        if not agente:
            return RedirectResponse("/login", status_code=303)

        # 1. Compañero
        companero = db.query(Agente).filter_by(id=companero_id, activo=True).first()
        if not companero:
            return _error("Compañero no encontrado")
        if companero.zona_id != agente.zona_id:
            return _error("El compañero es de otra zona")
        if companero.id == agente.id:
            return _error("No puedes cambiarte contigo mismo")

        # 2. Días
        if not (1 <= dia_solicitante <= 31 and 1 <= dia_companero <= 31):
            return _error("Día fuera de rango")
        hoy = date(2026, 5, 1)
        if dia_solicitante < hoy.day or dia_companero < hoy.day:
            return _error("No puedes cambiar días pasados")

        # 3. Registros
        reg_sol = (
            db.query(Cuadrante)
            .filter_by(agente_id=agente.id, mes=5, anio=2026, dia=dia_solicitante)
            .first()
        )
        reg_comp = (
            db.query(Cuadrante)
            .filter_by(agente_id=companero.id, mes=5, anio=2026, dia=dia_companero)
            .first()
        )
        if not reg_sol or not reg_sol.servicio:
            return _error("No tienes servicio ese día")
        if not reg_comp or not reg_comp.servicio:
            return _error("El compañero no tiene servicio ese día")

        # 4. Cambiables
        cambiables = {s.codigo for s in db.query(Servicio).filter_by(cambiable=True).all()}
        if reg_sol.servicio not in cambiables:
            return _error(f"Tu servicio ({reg_sol.servicio}) no es cambiable")
        if reg_comp.servicio not in cambiables:
            return _error(f"El servicio del compañero ({reg_comp.servicio}) no es cambiable")

        # 5. Días bloqueados
        fecha_sol = date(2026, 5, dia_solicitante)
        fecha_comp = date(2026, 5, dia_companero)

        bloqueo_sol = db.query(DiaBloqueado).filter(
            DiaBloqueado.fecha == fecha_sol,
            (DiaBloqueado.agente_id == agente.id) | (DiaBloqueado.zona_id == agente.zona_id),
        ).first()
        bloqueo_comp = db.query(DiaBloqueado).filter(
            DiaBloqueado.fecha == fecha_comp,
            (DiaBloqueado.agente_id == companero.id) | (DiaBloqueado.zona_id == companero.zona_id),
        ).first()
        if bloqueo_sol or bloqueo_comp:
            return _error("Póngase en contacto con el gestor (día bloqueado)")

        # 6. Restricciones
        r1 = db.query(Restriccion).filter_by(
            servicio_origen=reg_comp.servicio, servicio_destino=reg_sol.servicio
        ).first()
        r2 = db.query(Restriccion).filter_by(
            servicio_origen=reg_sol.servicio, servicio_destino=reg_comp.servicio
        ).first()
        if r1 or r2:
            return _error("Póngase en contacto con el gestor (incompatibilidad)")

        # 7. Duplicada
        dup = db.query(Solicitud).filter_by(
            solicitante_id=agente.id,
            companero_id=companero.id,
            dia_solicitante=dia_solicitante,
            dia_companero=dia_companero,
            estado="aprobada",
        ).first()
        if dup:
            return _error("Ya existe una solicitud idéntica aprobada")

        # ----------------- APLICAR -----------------
        srv_sol_original = reg_sol.servicio
        srv_comp_original = reg_comp.servicio

        reg_sol.servicio = srv_comp_original
        reg_comp.servicio = srv_sol_original

        solicitud = Solicitud(
            solicitante_id=agente.id,
            companero_id=companero.id,
            dia_solicitante=dia_solicitante,
            dia_companero=dia_companero,
            servicio_solicitante=srv_sol_original,
            servicio_companero=srv_comp_original,
            estado="aprobada",
            fecha_resolucion=datetime.utcnow(),
            mes=5,
            anio=2026,
        )
        db.add(solicitud)
        db.flush()

        db.add(CambioAplicado(solicitud_id=solicitud.id, volcado_excel=False))
        db.commit()

        return RedirectResponse(
            f"/solicitar-cambio?ok=Cambio+realizado:+día+{dia_solicitante}+↔+día+{dia_companero}",
            status_code=303,
        )
    finally:
        db.close()


# ------------------------------------------------------------------
# SALUD
# ------------------------------------------------------------------

@app.get("/salud")
def salud():
    return {"estado": "ok"}