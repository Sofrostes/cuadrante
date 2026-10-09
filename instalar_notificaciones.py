# instalar_notificaciones.py
"""
Instala la lógica de notificaciones:
- Badge rojo en inicio.html
- Banner de aviso si hay solicitudes pendientes
- Redirección automática a /solicitudes-pendientes al loguearse si las hay
- Plantilla solicitudes_pendientes.html

Ejecutar desde la raíz del proyecto:
    python instalar_notificaciones.py
"""
import os
import shutil
import zipfile
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
TPL_DIR = os.path.join(BASE, "app", "templates")
BACKUP_DIR = os.path.join(BASE, f"_backup_notif_{datetime.now():%Y%m%d_%H%M%S}")
ZIP_PATH = os.path.join(BASE, "notificaciones_cuadrantes.zip")
MAIN_PATH = os.path.join(BASE, "main.py")

os.makedirs(TPL_DIR, exist_ok=True)

# ==================================================================
# PLANTILLA inicio.html
# ==================================================================
INICIO_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Inicio · Cuadrantes</title>
    <style>
        * { box-sizing: border-box; }
        body { margin: 0; font-family: system-ui, sans-serif;
               background: #f1f5f9; color: #1e293b; padding: 2rem; }
        .container { max-width: 900px; margin: 0 auto; }
        header { display: flex; justify-content: space-between; align-items: center;
                 margin-bottom: 1.5rem; }
        h1 { margin: 0; font-size: 1.6rem; }
        .nav a { color: #3b82f6; text-decoration: none; margin-left: 1rem;
                 position: relative; display: inline-block; padding-right: 1.4rem; }
        .nav a:hover { text-decoration: underline; }
        .badge { position: absolute; top: -8px; right: -4px;
                 background: #ef4444; color: white; font-size: .7rem;
                 padding: 2px 6px; border-radius: 999px; font-weight: bold;
                 min-width: 18px; text-align: center; }
        .banner { background: #fef3c7; border-left: 4px solid #f59e0b;
                  padding: .75rem 1rem; border-radius: 6px; margin-bottom: 1.2rem;
                  color: #78350f; display: flex; justify-content: space-between;
                  align-items: center; gap: 1rem; flex-wrap: wrap; }
        .banner a { color: #b45309; font-weight: bold; text-decoration: underline; }
        .card { background: white; padding: 1.5rem; border-radius: 8px;
                box-shadow: 0 1px 3px rgba(0,0,0,.08); margin-bottom: 1rem; }
        .zona { display: block; padding: .8rem 1rem; background: #f8fafc;
                border: 1px solid #e2e8f0; border-radius: 6px;
                text-decoration: none; color: #1e293b; margin-bottom: .5rem; }
        .zona:hover { background: #eff6ff; border-color: #3b82f6; }
        .muted { color: #64748b; font-size: .9rem; }
    </style>
</head>
<body>
<div class="container">
    <header>
        <h1>Hola, {{ agente.nombre }}</h1>
        <nav class="nav">
            <a href="/solicitudes-pendientes">
                🔔 Mis solicitudes
                {% if pendientes and pendientes > 0 %}
                    <span class="badge">{{ pendientes }}</span>
                {% endif %}
            </a>
            <a href="/solicitar-cambio">Solicitar cambio</a>
            <a href="/logout">Salir</a>
        </nav>
    </header>

    {% if pendientes and pendientes > 0 %}
    <div class="banner">
        <span>
            🔔 Tienes <strong>{{ pendientes }}</strong>
            solicitud{{ 'es' if pendientes != 1 else '' }} de cambio pendiente{{ 's' if pendientes != 1 else '' }}.
        </span>
        <a href="/solicitudes-pendientes">Ver ahora →</a>
    </div>
    {% endif %}

    <div class="card">
        <h3 style="margin-top:0;">Zonas</h3>
        {% if zonas %}
            {% for z in zonas %}
            <a class="zona" href="/zona/{{ z.codigo }}">
                <strong>{{ z.codigo }}</strong> — {{ z.nombre }}
            </a>
            {% endfor %}
        {% else %}
            <p class="muted">No hay zonas cargadas todavía.</p>
        {% endif %}
    </div>
</div>
</body>
</html>
"""

# ==================================================================
# PLANTILLA solicitudes_pendientes.html
# ==================================================================
SOLICITUDES_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Solicitudes pendientes</title>
    <style>
        body { font-family: system-ui, sans-serif; background: #f1f5f9; color: #1e293b;
               margin: 0; padding: 2rem; }
        .container { max-width: 900px; margin: 0 auto; }
        h1 { margin-top: 0; }
        .card { background: white; padding: 1.2rem 1.5rem; border-radius: 8px;
                box-shadow: 0 1px 3px rgba(0,0,0,.08); margin-bottom: 1.5rem; }
        .card h3 { margin-top: 0; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: .55rem .7rem; text-align: left; border-bottom: 1px solid #e2e8f0;
                 font-size: .92rem; }
        th { background: #f8fafc; font-size: .8rem; color: #475569; text-transform: uppercase; }
        .btn { padding: .35rem .75rem; border-radius: 6px; border: none; cursor: pointer;
               font-size: .85rem; }
        .btn-success { background: #22c55e; color: white; }
        .btn-success:hover { background: #16a34a; }
        .btn-danger { background: #ef4444; color: white; }
        .btn-danger:hover { background: #dc2626; }
        .ok { background: #dcfce7; color: #166534; padding: .6rem 1rem;
              border-radius: 6px; margin-bottom: 1rem; }
        .error { background: #fee2e2; color: #991b1b; padding: .6rem 1rem;
                 border-radius: 6px; margin-bottom: 1rem; }
        .nav { margin-bottom: 1rem; }
        .nav a { color: #3b82f6; text-decoration: none; margin-right: 1rem; }
        .muted { color: #64748b; font-size: .85rem; }
    </style>
</head>
<body>
<div class="container">
    <div class="nav">
        <a href="/">← Inicio</a>
        <a href="/solicitar-cambio">Solicitar un cambio</a>
        <a href="/logout" style="float:right;">Salir</a>
    </div>

    <h1>🔔 Solicitudes de cambio</h1>

    {% if ok %}<div class="ok">{{ ok }}</div>{% endif %}
    {% if error %}<div class="error">{{ error }}</div>{% endif %}

    <div class="card">
        <h3>Te piden cambiar (pendientes de tu autorización)</h3>
        {% if pendientes %}
        <table>
            <thead>
                <tr><th>Compañero</th><th>Su día</th><th>Su servicio</th>
                    <th>Tu día</th><th>Tu servicio</th><th>Acciones</th></tr>
            </thead>
            <tbody>
                {% for s in pendientes %}
                <tr>
                    <td>{% set sol = solicitantes.get(s.solicitante_id) %}
                        {{ sol.nombre if sol else '?' }}</td>
                    <td>{{ s.dia_solicitante }}</td>
                    <td>{{ s.servicio_solicitante }}</td>
                    <td>{{ s.dia_companero }}</td>
                    <td>{{ s.servicio_companero }}</td>
                    <td style="display:flex; gap:.4rem;">
                        <form method="post" action="/solicitudes/{{ s.id }}/aceptar">
                            <button class="btn btn-success">Aceptar</button>
                        </form>
                        <form method="post" action="/solicitudes/{{ s.id }}/rechazar"
                              onsubmit="return confirm('¿Rechazar esta solicitud?')">
                            <button class="btn btn-danger">Rechazar</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <p class="muted">No tienes solicitudes pendientes.</p>
        {% endif %}
    </div>

    <div class="card">
        <h3>Has enviado (esperando respuesta)</h3>
        {% if enviadas %}
        <table>
            <thead>
                <tr><th>Compañero</th><th>Tu día</th><th>Su día</th><th>Estado</th></tr>
            </thead>
            <tbody>
                {% for s in enviadas %}
                <tr>
                    <td>{% set comp = companeros.get(s.companero_id) %}
                        {{ comp.nombre if comp else '?' }}</td>
                    <td>{{ s.dia_solicitante }} ({{ s.servicio_solicitante }})</td>
                    <td>{{ s.dia_companero }} ({{ s.servicio_companero }})</td>
                    <td>⏳ Pendiente</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <p class="muted">No has enviado ninguna solicitud pendiente.</p>
        {% endif %}
    </div>
</div>
</body>
</html>
"""

# ==================================================================
# PARCHE para POST /login (redirección si hay pendientes)
# ==================================================================
BLOQUE_LOGIN_ANTIGUO = """        token = crear_sesion(db, agente)
        destino = "/cambiar-pin" if agente.debe_cambiar_pin else "/"
        respuesta = RedirectResponse(destino, status_code=303)
        respuesta.set_cookie("sesion", token, httponly=True,
                             max_age=DURACION_SESION_HORAS * 3600, samesite="lax")
        return respuesta"""

BLOQUE_LOGIN_NUEVO = """        token = crear_sesion(db, agente)

        # Decidir destino: cambio de PIN > bandeja con pendientes > inicio
        if agente.debe_cambiar_pin:
            destino = "/cambiar-pin"
        else:
            n_pend = db.query(Solicitud).filter_by(
                companero_id=agente.id, estado="pendiente").count()
            destino = "/solicitudes-pendientes" if n_pend > 0 else "/"

        respuesta = RedirectResponse(destino, status_code=303)
        respuesta.set_cookie("sesion", token, httponly=True,
                             max_age=DURACION_SESION_HORAS * 3600, samesite="lax")
        return respuesta"""


# ==================================================================
# INSTALACIÓN
# ==================================================================
def backup(ruta):
    if os.path.exists(ruta):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        shutil.copy2(ruta, os.path.join(BACKUP_DIR, os.path.basename(ruta)))
        return True
    return False


def escribir_plantillas():
    for nombre, contenido in {
        "inicio.html": INICIO_HTML,
        "solicitudes_pendientes.html": SOLICITUDES_HTML,
    }.items():
        destino = os.path.join(TPL_DIR, nombre)
        backup(destino)
        with open(destino, "w", encoding="utf-8") as f:
            f.write(contenido)
        print(f"✅ {nombre} escrito")


def parchear_main():
    if not os.path.exists(MAIN_PATH):
        print("⚠️  No se encontró main.py, se omite el parche")
        return

    backup(MAIN_PATH)
    with open(MAIN_PATH, "r", encoding="utf-8") as f:
        contenido = f.read()

    if "n_pend = db.query(Solicitud)" in contenido:
        print("ℹ️  main.py ya estaba parcheado, no se toca")
        return

    if BLOQUE_LOGIN_ANTIGUO not in contenido:
        print("⚠️  No se encontró el bloque de login esperado en main.py.")
        print("    Revisa manualmente el endpoint POST /login y aplica el cambio:")
        print(BLOQUE_LOGIN_NUEVO)
        return

    contenido = contenido.replace(BLOQUE_LOGIN_ANTIGUO, BLOQUE_LOGIN_NUEVO, 1)
    with open(MAIN_PATH, "w", encoding="utf-8") as f:
        f.write(contenido)
    print("✅ main.py parcheado (POST /login redirige a bandeja si hay pendientes)")


def crear_zip():
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as z:
        for n in ("inicio.html", "solicitudes_pendientes.html"):
            ruta = os.path.join(TPL_DIR, n)
            if os.path.exists(ruta):
                z.write(ruta, arcname=f"app/templates/{n}")
        if os.path.exists(MAIN_PATH):
            z.write(MAIN_PATH, arcname="main.py")
    print(f"📦 ZIP creado: {ZIP_PATH}")


if __name__ == "__main__":
    print("📁 Plantillas destino:", TPL_DIR)
    print("📄 main.py:", MAIN_PATH)
    print()
    escribir_plantillas()
    print()
    parchear_main()
    print()
    crear_zip()
    if os.path.exists(BACKUP_DIR):
        print(f"\n🗂️  Backup en: {BACKUP_DIR}")
    print("\n👉 Ahora:")
    print("   1) uvicorn main:app --reload")
    print("   2) Login como agente 1002 (que tiene solicitudes pendientes)")
    print("      → te redirige automáticamente a /solicitudes-pendientes")
    print("   3) En / (inicio) verás el badge rojo y el banner amarillo")
    print("   4) Acepta o rechaza desde la bandeja")