import secrets
import bcrypt
from datetime import datetime, timedelta, date
from urllib.parse import quote

from fastapi import FastAPI, Request, HTTPException, Form, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.db.conexion import crear_tablas, SessionLocal
from app.db.modelos import (
    Zona, Agente, Cuadrante, Sesion, Servicio,
    DiaBloqueado, Restriccion, Solicitud, CambioAplicado,
    Admin, SesionAdmin,
)

# ------------------------------------------------------------------
# CONFIGURACIÓN
# ------------------------------------------------------------------

PIN_INICIAL = "1234"
DURACION_SESION_HORAS = 8
DURACION_SESION_ADMIN_HORAS = 24

ADMIN_INICIAL_USUARIO = "2354"
ADMIN_INICIAL_PASSWORD = "Admin2026!"
ADMIN_INICIAL_NOMBRE = "Administrador principal"

app = FastAPI(title="Cuadrantes")
templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
def al_arrancar():
    crear_tablas()
    _crear_admin_inicial()
    print("✅ Base de datos lista")


def _crear_admin_inicial():
    db = SessionLocal()
    try:
        if db.query(Admin).count() == 0:
            db.add(Admin(
                usuario=ADMIN_INICIAL_USUARIO,
                password_hash=bcrypt.hashpw(
                    ADMIN_INICIAL_PASSWORD.encode("utf-8"),
                    bcrypt.gensalt(),
                ).decode("utf-8"),
                nombre=ADMIN_INICIAL_NOMBRE,
                activo=True,
            ))
            db.commit()
            print(f"👤 Admin inicial creado: {ADMIN_INICIAL_USUARIO} / {ADMIN_INICIAL_PASSWORD}")
    finally:
        db.close()


# ------------------------------------------------------------------
# HELPERS DE SESIÓN DE AGENTE
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
# HELPERS DE SESIÓN DE ADMIN
# ------------------------------------------------------------------

def crear_sesion_admin(db, admin: Admin) -> str:
    token = secrets.token_urlsafe(32)
    expira = datetime.utcnow() + timedelta(hours=DURACION_SESION_ADMIN_HORAS)
    db.add(SesionAdmin(token=token, admin_id=admin.id, expira=expira))
    db.commit()
    return token


def admin_de_sesion(db, token: str | None) -> Admin | None:
    if not token:
        return None
    sesion = db.query(SesionAdmin).filter_by(token=token).first()
    if not sesion:
        return None
    if sesion.expira < datetime.utcnow():
        db.delete(sesion)
        db.commit()
        return None
    return db.query(Admin).filter_by(id=sesion.admin_id).first()


def cerrar_sesion_admin(db, token: str | None):
    if not token:
        return
    sesion = db.query(SesionAdmin).filter_by(token=token).first()
    if sesion:
        db.delete(sesion)
        db.commit()


def _error_cambio(msg: str):
    return RedirectResponse(f"/solicitar-cambio?error={quote(msg)}", status_code=303)


# ------------------------------------------------------------------
# LOGIN / LOGOUT AGENTE
# ------------------------------------------------------------------

@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request, error: str | None = None):
    return templates.TemplateResponse(
        request=request, name="login.html", context={"error": error},
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
        respuesta.set_cookie("sesion", token, httponly=True,
                             max_age=DURACION_SESION_HORAS * 3600, samesite="lax")
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
            request=request, name="cambiar_pin.html",
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
# VISTAS PROTEGIDAS (AGENTE)
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
            request=request, name="inicio.html",
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

        agentes = (db.query(Agente)
                   .filter_by(zona_id=zona.id, activo=True)
                   .order_by(Agente.fila_excel).all())

        dias = list(range(1, 32))
        matriz = {ag.id: {d: "" for d in dias} for ag in agentes}

        if agentes:
            filas = (db.query(Cuadrante)
                     .filter(Cuadrante.mes == mes,
                             Cuadrante.anio == anio,
                             Cuadrante.agente_id.in_([a.id for a in agentes]))
                     .all())
            for reg in filas:
                matriz[reg.agente_id][reg.dia] = reg.servicio or ""

        return templates.TemplateResponse(
            request=request, name="zona.html",
            context={
                "agente_logueado": agente, "zona": zona, "agentes": agentes,
                "dias": dias, "matriz": matriz, "mes": mes, "anio": anio,
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
    db = SessionLocal()
    try:
        agente = agente_de_sesion(db, sesion)
        if not agente:
            return RedirectResponse("/login", status_code=303)
        if agente.debe_cambiar_pin:
            return RedirectResponse("/cambiar-pin", status_code=303)

        hoy = date(2026, 5, 1)

        companeros = (db.query(Agente)
                      .filter(Agente.zona_id == agente.zona_id,
                              Agente.activo == True,
                              Agente.id != agente.id)
                      .order_by(Agente.fila_excel).all())

        mis_registros = (db.query(Cuadrante)
                         .filter(Cuadrante.agente_id == agente.id,
                                 Cuadrante.mes == 5, Cuadrante.anio == 2026,
                                 Cuadrante.dia >= hoy.day)
                         .order_by(Cuadrante.dia).all())

        otros_ids = [c.id for c in companeros]
        cuadrante_companeros = (db.query(Cuadrante)
                                .filter(Cuadrante.agente_id.in_(otros_ids),
                                        Cuadrante.mes == 5, Cuadrante.anio == 2026,
                                        Cuadrante.dia >= hoy.day)
                                .all() if otros_ids else [])

        matriz_companeros = {c.id: {} for c in companeros}
        for reg in cuadrante_companeros:
            matriz_companeros[reg.agente_id][reg.dia] = reg.servicio or ""

        servicios_cambiables = {s.codigo for s in db.query(Servicio).filter_by(cambiable=True).all()}

        return templates.TemplateResponse(
            request=request, name="solicitar_cambio.html",
            context={
                "agente": agente, "companeros": companeros,
                "mis_registros": mis_registros,
                "matriz_companeros": matriz_companeros,
                "servicios_cambiables": servicios_cambiables,
                "error": error, "ok": ok,
            },
        )
    finally:
        db.close()


def _servicio_en_dia(db, agente_id: int, dia: int) -> str | None:
    """Devuelve el servicio de un agente en un día concreto o None si no existe."""
    if dia < 1 or dia > 31:
        return None
    reg = (db.query(Cuadrante)
           .filter_by(agente_id=agente_id, mes=5, anio=2026, dia=dia).first())
    return reg.servicio if reg and reg.servicio else None


def _hay_restriccion(db, s1: str, s2: str) -> bool:
    """True si existe restricción s1→s2 o s2→s1."""
    if not s1 or not s2:
        return False
    r1 = db.query(Restriccion).filter_by(servicio_origen=s1, servicio_destino=s2).first()
    r2 = db.query(Restriccion).filter_by(servicio_origen=s2, servicio_destino=s1).first()
    return bool(r1 or r2)


@app.post("/solicitar-cambio", response_class=HTMLResponse)
def solicitar_cambio(
    request: Request,
    dia_solicitante: int = Form(...),
    companero_id: int = Form(...),
    dia_companero: int = Form(...),
    sesion: str | None = Cookie(default=None),
):
    db = SessionLocal()
    try:
        agente = agente_de_sesion(db, sesion)
        if not agente:
            return RedirectResponse("/login", status_code=303)

        # 1. Compañero
        companero = db.query(Agente).filter_by(id=companero_id, activo=True).first()
        if not companero:
            return _error_cambio("Compañero no encontrado")
        if companero.zona_id != agente.zona_id:
            return _error_cambio("El compañero es de otra zona")
        if companero.id == agente.id:
            return _error_cambio("No puedes cambiarte contigo mismo")

        # 2. Días
        if not (1 <= dia_solicitante <= 31 and 1 <= dia_companero <= 31):
            return _error_cambio("Día fuera de rango")
        hoy = date(2026, 5, 1)
        if dia_solicitante < hoy.day or dia_companero < hoy.day:
            return _error_cambio("No puedes cambiar días pasados")

        # 3. Registros
        reg_sol = db.query(Cuadrante).filter_by(
            agente_id=agente.id, mes=5, anio=2026, dia=dia_solicitante).first()
        reg_comp = db.query(Cuadrante).filter_by(
            agente_id=companero.id, mes=5, anio=2026, dia=dia_companero).first()
        if not reg_sol or not reg_sol.servicio:
            return _error_cambio("No tienes servicio ese día")
        if not reg_comp or not reg_comp.servicio:
            return _error_cambio("El compañero no tiene servicio ese día")

        # 4. Cambiables
        cambiables = {s.codigo for s in db.query(Servicio).filter_by(cambiable=True).all()}
        if reg_sol.servicio not in cambiables:
            return _error_cambio(f"Tu servicio ({reg_sol.servicio}) no es cambiable")
        if reg_comp.servicio not in cambiables:
            return _error_cambio(f"El servicio del compañero ({reg_comp.servicio}) no es cambiable")

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
            return _error_cambio("Póngase en contacto con el gestor (día bloqueado)")

        # 6. Restricciones:
        #    6a) entre los dos servicios intercambiados
        srv_sol_original = reg_sol.servicio
        srv_comp_original = reg_comp.servicio

        if _hay_restriccion(db, srv_sol_original, srv_comp_original):
            return _error_cambio("Póngase en contacto con el gestor (incompatibilidad)")

        #    6b) A pasa a hacer srv_comp_original en dia_solicitante
        #        → comprobar día anterior y posterior de A
        srv_ant_sol = _servicio_en_dia(db, agente.id, dia_solicitante - 1)
        srv_post_sol = _servicio_en_dia(db, agente.id, dia_solicitante + 1)
        if _hay_restriccion(db, srv_comp_original, srv_ant_sol) or _hay_restriccion(db, srv_comp_original, srv_post_sol):
            return _error_cambio("Póngase en contacto con el gestor (incompatibilidad con día adyacente)")

        #    6c) B pasa a hacer srv_sol_original en dia_companero
        #        → comprobar día anterior y posterior de B
        srv_ant_comp = _servicio_en_dia(db, companero.id, dia_companero - 1)
        srv_post_comp = _servicio_en_dia(db, companero.id, dia_companero + 1)
        if _hay_restriccion(db, srv_sol_original, srv_ant_comp) or _hay_restriccion(db, srv_sol_original, srv_post_comp):
            return _error_cambio("Póngase en contacto con el gestor (incompatibilidad con día adyacente)")

        # 7. Duplicada
        dup = db.query(Solicitud).filter_by(
            solicitante_id=agente.id, companero_id=companero.id,
            dia_solicitante=dia_solicitante, dia_companero=dia_companero,
            estado="aprobada",
        ).first()
        if dup:
            return _error_cambio("Ya existe una solicitud idéntica aprobada")

        # ----------------- APLICAR -----------------
        reg_sol.servicio = srv_comp_original
        reg_comp.servicio = srv_sol_original

        solicitud = Solicitud(
            solicitante_id=agente.id, companero_id=companero.id,
            dia_solicitante=dia_solicitante, dia_companero=dia_companero,
            servicio_solicitante=srv_sol_original,
            servicio_companero=srv_comp_original,
            estado="aprobada", fecha_resolucion=datetime.utcnow(),
            mes=5, anio=2026,
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


# ==================================================================
# ===============        PANEL DE ADMINISTRACIÓN       =============
# ==================================================================

# ------------------------------------------------------------------
# LOGIN / LOGOUT ADMIN
# ------------------------------------------------------------------

@app.get("/admin/login", response_class=HTMLResponse)
def admin_login_form(request: Request, error: str | None = None):
    return templates.TemplateResponse(
        request=request, name="admin_login.html", context={"error": error},
    )


@app.post("/admin/login", response_class=HTMLResponse)
def admin_login(
    request: Request,
    usuario: str = Form(...),
    password: str = Form(...),
):
    db = SessionLocal()
    try:
        admin = db.query(Admin).filter_by(usuario=usuario.strip(), activo=True).first()
        if not admin or not bcrypt.checkpw(password.encode("utf-8"), admin.password_hash.encode("utf-8")):
            return RedirectResponse("/admin/login?error=Credenciales+incorrectas", status_code=303)

        token = crear_sesion_admin(db, admin)
        respuesta = RedirectResponse("/admin", status_code=303)
        respuesta.set_cookie("sesion_admin", token, httponly=True,
                             max_age=DURACION_SESION_ADMIN_HORAS * 3600, samesite="lax")
        return respuesta
    finally:
        db.close()


@app.get("/admin/logout")
def admin_logout(request: Request, sesion_admin: str | None = Cookie(default=None)):
    db = SessionLocal()
    try:
        cerrar_sesion_admin(db, sesion_admin)
    finally:
        db.close()
    respuesta = RedirectResponse("/admin/login", status_code=303)
    respuesta.delete_cookie("sesion_admin")
    return respuesta


def _require_admin(db, token: str | None) -> Admin | None:
    return admin_de_sesion(db, token)


# ------------------------------------------------------------------
# PANEL ADMIN - HOME
# ------------------------------------------------------------------

@app.get("/admin", response_class=HTMLResponse)
def admin_home(request: Request, sesion_admin: str | None = Cookie(default=None)):
    db = SessionLocal()
    try:
        admin = _require_admin(db, sesion_admin)
        if not admin:
            return RedirectResponse("/admin/login", status_code=303)
        return RedirectResponse("/admin/restricciones", status_code=303)
    finally:
        db.close()


# ------------------------------------------------------------------
# ADMIN - RESTRICCIONES
# ------------------------------------------------------------------

@app.get("/admin/restricciones", response_class=HTMLResponse)
def admin_restricciones(
    request: Request,
    sesion_admin: str | None = Cookie(default=None),
    ok: str | None = None,
    error: str | None = None,
):
    db = SessionLocal()
    try:
        admin = _require_admin(db, sesion_admin)
        if not admin:
            return RedirectResponse("/admin/login", status_code=303)

        restricciones = db.query(Restriccion).order_by(
            Restriccion.servicio_origen, Restriccion.servicio_destino).all()
        servicios = db.query(Servicio).order_by(Servicio.codigo).all()

        return templates.TemplateResponse(
            request=request, name="admin_restricciones.html",
            context={
                "admin": admin, "seccion": "restricciones",
                "restricciones": restricciones, "servicios": servicios,
                "ok": ok, "error": error,
            },
        )
    finally:
        db.close()


@app.post("/admin/restricciones/añadir")
def admin_restricciones_añadir(
    servicio_origen: str = Form(...),
    servicio_destino: str = Form(...),
    motivo: str = Form(""),
    sesion_admin: str | None = Cookie(default=None),
):
    db = SessionLocal()
    try:
        admin = _require_admin(db, sesion_admin)
        if not admin:
            return RedirectResponse("/admin/login", status_code=303)

        if servicio_origen == servicio_destino:
            return RedirectResponse("/admin/restricciones?error=Origen+y+destino+iguales", status_code=303)

        dup = db.query(Restriccion).filter_by(
            servicio_origen=servicio_origen, servicio_destino=servicio_destino).first()
        if dup:
            return RedirectResponse("/admin/restricciones?error=Ya+existe", status_code=303)

        db.add(Restriccion(
            servicio_origen=servicio_origen,
            servicio_destino=servicio_destino,
            motivo=motivo or None,
        ))
        db.commit()
        return RedirectResponse("/admin/restricciones?ok=Añadida", status_code=303)
    finally:
        db.close()


@app.post("/admin/restricciones/{rid}/eliminar")
def admin_restricciones_eliminar(
    rid: int,
    sesion_admin: str | None = Cookie(default=None),
):
    db = SessionLocal()
    try:
        admin = _require_admin(db, sesion_admin)
        if not admin:
            return RedirectResponse("/admin/login", status_code=303)
        r = db.query(Restriccion).filter_by(id=rid).first()
        if r:
            db.delete(r)
            db.commit()
        return RedirectResponse("/admin/restricciones?ok=Eliminada", status_code=303)
    finally:
        db.close()


# ------------------------------------------------------------------
# ADMIN - BLOQUEOS
# ------------------------------------------------------------------

@app.get("/admin/bloqueos", response_class=HTMLResponse)
def admin_bloqueos(
    request: Request,
    sesion_admin: str | None = Cookie(default=None),
    ok: str | None = None,
    error: str | None = None,
):
    db = SessionLocal()
    try:
        admin = _require_admin(db, sesion_admin)
        if not admin:
            return RedirectResponse("/admin/login", status_code=303)

        bloqueos = (db.query(DiaBloqueado)
                    .order_by(DiaBloqueado.fecha).all())
        agentes = db.query(Agente).order_by(Agente.nombre).all()
        zonas = db.query(Zona).order_by(Zona.codigo).all()

        return templates.TemplateResponse(
            request=request, name="admin_bloqueos.html",
            context={
                "admin": admin, "seccion": "bloqueos",
                "bloqueos": bloqueos, "agentes": agentes, "zonas": zonas,
                "ok": ok, "error": error,
            },
        )
    finally:
        db.close()


@app.post("/admin/bloqueos/añadir")
def admin_bloqueos_añadir(
    fecha: str = Form(...),
    agente_id: str = Form(""),
    zona_id: str = Form(""),
    motivo: str = Form(""),
    sesion_admin: str | None = Cookie(default=None),
):
    db = SessionLocal()
    try:
        admin = _require_admin(db, sesion_admin)
        if not admin:
            return RedirectResponse("/admin/login", status_code=303)

        try:
            fecha_dt = datetime.strptime(fecha, "%Y-%m-%d").date()
        except ValueError:
            return RedirectResponse("/admin/bloqueos?error=Fecha+inválida", status_code=303)

        agente_id_int = int(agente_id) if agente_id.strip() else None
        zona_id_int = int(zona_id) if zona_id.strip() else None

        if not agente_id_int and not zona_id_int:
            return RedirectResponse("/admin/bloqueos?error=Debes+elegir+agente+o+zona", status_code=303)

        db.add(DiaBloqueado(
            agente_id=agente_id_int,
            zona_id=zona_id_int,
            fecha=fecha_dt,
            motivo=motivo or None,
        ))
        db.commit()
        return RedirectResponse("/admin/bloqueos?ok=Añadido", status_code=303)
    finally:
        db.close()


@app.post("/admin/bloqueos/{bid}/eliminar")
def admin_bloqueos_eliminar(
    bid: int,
    sesion_admin: str | None = Cookie(default=None),
):
    db = SessionLocal()
    try:
        admin = _require_admin(db, sesion_admin)
        if not admin:
            return RedirectResponse("/admin/login", status_code=303)
        b = db.query(DiaBloqueado).filter_by(id=bid).first()
        if b:
            db.delete(b)
            db.commit()
        return RedirectResponse("/admin/bloqueos?ok=Eliminado", status_code=303)
    finally:
        db.close()


# ------------------------------------------------------------------
# ADMIN - AGENTES
# ------------------------------------------------------------------

@app.get("/admin/agentes", response_class=HTMLResponse)
def admin_agentes(
    request: Request,
    sesion_admin: str | None = Cookie(default=None),
    ok: str | None = None,
    error: str | None = None,
):
    db = SessionLocal()
    try:
        admin = _require_admin(db, sesion_admin)
        if not admin:
            return RedirectResponse("/admin/login", status_code=303)

        agentes = (db.query(Agente)
                   .order_by(Agente.zona_id, Agente.fila_excel).all())
        zonas = {z.id: z.codigo for z in db.query(Zona).all()}

        return templates.TemplateResponse(
            request=request, name="admin_agentes.html",
            context={
                "admin": admin, "seccion": "agentes",
                "agentes": agentes, "zonas": zonas,
                "ok": ok, "error": error,
            },
        )
    finally:
        db.close()


@app.post("/admin/agentes/{aid}/reset-pin")
def admin_agentes_reset_pin(
    aid: int,
    sesion_admin: str | None = Cookie(default=None),
):
    db = SessionLocal()
    try:
        admin = _require_admin(db, sesion_admin)
        if not admin:
            return RedirectResponse("/admin/login", status_code=303)
        ag = db.query(Agente).filter_by(id=aid).first()
        if ag:
            ag.pin_hash = None
            ag.debe_cambiar_pin = False
            db.commit()
        return RedirectResponse("/admin/agentes?ok=PIN+reseteado+(vuelve+a+1234)", status_code=303)
    finally:
        db.close()


@app.post("/admin/agentes/{aid}/toggle-activo")
def admin_agentes_toggle(
    aid: int,
    sesion_admin: str | None = Cookie(default=None),
):
    db = SessionLocal()
    try:
        admin = _require_admin(db, sesion_admin)
        if not admin:
            return RedirectResponse("/admin/login", status_code=303)
        ag = db.query(Agente).filter_by(id=aid).first()
        if ag:
            ag.activo = not ag.activo
            db.commit()
        return RedirectResponse("/admin/agentes?ok=Actualizado", status_code=303)
    finally:
        db.close()


# ------------------------------------------------------------------
# ADMIN - INFORME
# ------------------------------------------------------------------

@app.get("/admin/informe", response_class=HTMLResponse)
def admin_informe(
    request: Request,
    sesion_admin: str | None = Cookie(default=None),
    ok: str | None = None,
):
    db = SessionLocal()
    try:
        admin = _require_admin(db, sesion_admin)
        if not admin:
            return RedirectResponse("/admin/login", status_code=303)

        desde = datetime.utcnow() - timedelta(days=7)
        cambios = (db.query(CambioAplicado, Solicitud)
                   .join(Solicitud, CambioAplicado.solicitud_id == Solicitud.id)
                   .filter(CambioAplicado.fecha_aplicacion >= desde)
                   .order_by(CambioAplicado.fecha_aplicacion.desc())
                   .all())

        agentes_map = {a.id: a for a in db.query(Agente).all()}
        pendientes = db.query(CambioAplicado).filter_by(volcado_excel=False).count()

        filas = []
        for cambio, solicitud in cambios:
            filas.append({
                "id": cambio.id,
                "fecha": cambio.fecha_aplicacion,
                "solicitante": agentes_map.get(solicitud.solicitante_id),
                "companero": agentes_map.get(solicitud.companero_id),
                "dia_solicitante": solicitud.dia_solicitante,
                "dia_companero": solicitud.dia_companero,
                "serv_solicitante": solicitud.servicio_solicitante,
                "serv_companero": solicitud.servicio_companero,
                "volcado": cambio.volcado_excel,
            })

        return templates.TemplateResponse(
            request=request, name="admin_informe.html",
            context={
                "admin": admin, "seccion": "informe",
                "filas": filas, "pendientes": pendientes, "ok": ok,
            },
        )
    finally:
        db.close()


@app.post("/admin/informe/forzar-volcado")
def admin_informe_forzar(sesion_admin: str | None = Cookie(default=None)):
    db = SessionLocal()
    try:
        admin = _require_admin(db, sesion_admin)
        if not admin:
            return RedirectResponse("/admin/login", status_code=303)
        # En el PASO 17 haremos el vol