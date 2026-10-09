# instalar_todo.py
"""
Crea todas las plantillas necesarias para el panel admin y solicitudes pendientes.
Hace backup de las existentes y genera un ZIP con todo.
"""
import os
import shutil
import zipfile
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
TPL_DIR = os.path.join(BASE, "app", "templates")
BACKUP_DIR = os.path.join(BASE, f"_backup_{datetime.now():%Y%m%d_%H%M%S}")
ZIP_PATH = os.path.join(BASE, "plantillas_cuadrantes.zip")

os.makedirs(TPL_DIR, exist_ok=True)

PLANTILLAS = {}

# ------------------------------------------------------------------
PLANTILLAS["admin_login.html"] = r"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Admin · Cuadrantes</title>
    <style>
        body { font-family: system-ui, sans-serif; background: #1e293b; color: #e2e8f0;
               display: flex; justify-content: center; align-items: center;
               min-height: 100vh; margin: 0; }
        .card { background: #334155; padding: 2rem 2.5rem; border-radius: 12px;
                box-shadow: 0 10px 25px rgba(0,0,0,.3); width: 320px; }
        h1 { margin-top: 0; font-size: 1.3rem; text-align: center; color: #f1f5f9; }
        label { display: block; margin: .8rem 0 .3rem; font-size: .9rem; }
        input { width: 100%; padding: .6rem; border-radius: 6px; border: 1px solid #475569;
                background: #1e293b; color: #f1f5f9; box-sizing: border-box; }
        button { width: 100%; margin-top: 1.2rem; padding: .7rem; border: none;
                 border-radius: 6px; background: #3b82f6; color: white;
                 font-size: 1rem; cursor: pointer; }
        button:hover { background: #2563eb; }
        .error { background: #7f1d1d; padding: .6rem; border-radius: 6px;
                 margin-bottom: 1rem; font-size: .9rem; text-align: center; }
    </style>
</head>
<body>
    <div class="card">
        <h1>🔐 Panel de administración</h1>
        {% if error %}
            <div class="error">{{ error }}</div>
        {% endif %}
        <form method="post" action="/admin/login">
            <label>Usuario</label>
            <input type="text" name="usuario" required autofocus>
            <label>Contraseña</label>
            <input type="password" name="password" required>
            <button type="submit">Entrar</button>
        </form>
    </div>
</body>
</html>
"""

# ------------------------------------------------------------------
PLANTILLAS["admin_base.html"] = r"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>{% block title %}Admin{% endblock %} · Cuadrantes</title>
    <style>
        * { box-sizing: border-box; }
        body { margin: 0; font-family: system-ui, sans-serif; background: #f1f5f9; color: #1e293b; }
        .layout { display: flex; min-height: 100vh; }
        .sidebar { width: 220px; background: #1e293b; color: #e2e8f0; padding: 1.5rem 1rem; }
        .sidebar h2 { font-size: 1rem; margin-top: 0; color: #94a3b8; text-transform: uppercase;
                      letter-spacing: .05em; }
        .sidebar a { display: block; padding: .6rem .8rem; color: #cbd5e1;
                     text-decoration: none; border-radius: 6px; margin-bottom: .25rem; }
        .sidebar a:hover { background: #334155; }
        .sidebar a.active { background: #3b82f6; color: white; }
        .sidebar .logout { margin-top: 2rem; color: #f87171; }
        .content { flex: 1; padding: 2rem; }
        .content h1 { margin-top: 0; }
        table { width: 100%; border-collapse: collapse; background: white;
                border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
        th, td { padding: .6rem .8rem; text-align: left; border-bottom: 1px solid #e2e8f0; }
        th { background: #f8fafc; font-size: .85rem; color: #475569; text-transform: uppercase; }
        tr:last-child td { border-bottom: none; }
        .ok { background: #dcfce7; color: #166534; padding: .6rem 1rem; border-radius: 6px;
              margin-bottom: 1rem; }
        .error { background: #fee2e2; color: #991b1b; padding: .6rem 1rem; border-radius: 6px;
                 margin-bottom: 1rem; }
        .btn { padding: .4rem .8rem; border-radius: 6px; border: none; cursor: pointer;
               font-size: .9rem; }
        .btn-primary { background: #3b82f6; color: white; }
        .btn-primary:hover { background: #2563eb; }
        .btn-danger { background: #ef4444; color: white; }
        .btn-danger:hover { background: #dc2626; }
        .btn-secondary { background: #64748b; color: white; }
        .card { background: white; padding: 1.5rem; border-radius: 8px;
                box-shadow: 0 1px 3px rgba(0,0,0,.08); margin-bottom: 1.5rem; }
        .card h3 { margin-top: 0; }
        form.inline { display: flex; gap: .6rem; align-items: flex-end; flex-wrap: wrap; }
        form.inline label { display: flex; flex-direction: column; font-size: .8rem; color: #475569; }
        form.inline input, form.inline select { padding: .45rem; border: 1px solid #cbd5e1;
                                                border-radius: 6px; }
    </style>
</head>
<body>
    <div class="layout">
        <aside class="sidebar">
            <h2>Admin</h2>
            <a href="/admin/restricciones" class="{% if seccion == 'restricciones' %}active{% endif %}">Restricciones</a>
            <a href="/admin/bloqueos"     class="{% if seccion == 'bloqueos' %}active{% endif %}">Bloqueos</a>
            <a href="/admin/agentes"      class="{% if seccion == 'agentes' %}active{% endif %}">Agentes</a>
            <a href="/admin/informe"      class="{% if seccion == 'informe' %}active{% endif %}">Informe</a>
            <a href="/admin/solicitudes"  class="{% if seccion == 'solicitudes' %}active{% endif %}">Solicitudes</a>
            <a href="/admin/logout" class="logout">Cerrar sesión</a>
        </aside>
        <main class="content">
            {% if ok %}<div class="ok">{{ ok }}</div>{% endif %}
            {% if error %}<div class="error">{{ error }}</div>{% endif %}
            {% block content %}{% endblock %}
        </main>
    </div>
</body>
</html>
"""

# ------------------------------------------------------------------
PLANTILLAS["admin_restricciones.html"] = r"""{% extends "admin_base.html" %}
{% block title %}Restricciones{% endblock %}
{% block content %}
<h1>Restricciones entre servicios</h1>

<div class="card">
    <h3>Añadir restricción</h3>
    <form method="post" action="/admin/restricciones/añadir" class="inline">
        <label>Origen
            <select name="servicio_origen" required>
                {% for s in servicios %}
                    <option value="{{ s.codigo }}">{{ s.codigo }} — {{ s.descripcion or '' }}</option>
                {% endfor %}
            </select>
        </label>
        <label>Destino
            <select name="servicio_destino" required>
                {% for s in servicios %}
                    <option value="{{ s.codigo }}">{{ s.codigo }} — {{ s.descripcion or '' }}</option>
                {% endfor %}
            </select>
        </label>
        <label>Motivo
            <input type="text" name="motivo" placeholder="opcional">
        </label>
        <button type="submit" class="btn btn-primary">Añadir</button>
    </form>
</div>

<table>
    <thead>
        <tr><th>Origen</th><th>Destino</th><th>Motivo</th><th></th></tr>
    </thead>
    <tbody>
        {% for r in restricciones %}
        <tr>
            <td>{{ r.servicio_origen }}</td>
            <td>{{ r.servicio_destino }}</td>
            <td>{{ r.motivo or '—' }}</td>
            <td>
                <form method="post" action="/admin/restricciones/{{ r.id }}/eliminar"
                      onsubmit="return confirm('¿Eliminar?')">
                    <button class="btn btn-danger">Eliminar</button>
                </form>
            </td>
        </tr>
        {% else %}
        <tr><td colspan="4">Sin restricciones.</td></tr>
        {% endfor %}
    </tbody>
</table>
{% endblock %}
"""

# ------------------------------------------------------------------
PLANTILLAS["admin_bloqueos.html"] = r"""{% extends "admin_base.html" %}
{% block title %}Bloqueos{% endblock %}
{% block content %}
<h1>Días bloqueados</h1>

<div class="card">
    <h3>Añadir bloqueo</h3>
    <form method="post" action="/admin/bloqueos/añadir" class="inline">
        <label>Fecha
            <input type="date" name="fecha" required>
        </label>
        <label>Agente (opcional)
            <select name="agente_id">
                <option value="">— ninguno —</option>
                {% for a in agentes %}
                    <option value="{{ a.id }}">{{ a.num_agente }} — {{ a.nombre }}</option>
                {% endfor %}
            </select>
        </label>
        <label>Zona (opcional)
            <select name="zona_id">
                <option value="">— ninguna —</option>
                {% for z in zonas %}
                    <option value="{{ z.id }}">{{ z.codigo }}</option>
                {% endfor %}
            </select>
        </label>
        <label>Motivo
            <input type="text" name="motivo" placeholder="opcional">
        </label>
        <button type="submit" class="btn btn-primary">Añadir</button>
    </form>
</div>

<table>
    <thead>
        <tr><th>Fecha</th><th>Agente</th><th>Zona</th><th>Motivo</th><th></th></tr>
    </thead>
    <tbody>
        {% for b in bloqueos %}
        <tr>
            <td>{{ b.fecha }}</td>
            <td>{{ b.agente_id or '—' }}</td>
            <td>{{ b.zona_id or '—' }}</td>
            <td>{{ b.motivo or '—' }}</td>
            <td>
                <form method="post" action="/admin/bloqueos/{{ b.id }}/eliminar"
                      onsubmit="return confirm('¿Eliminar?')">
                    <button class="btn btn-danger">Eliminar</button>
                </form>
            </td>
        </tr>
        {% else %}
        <tr><td colspan="5">Sin bloqueos.</td></tr>
        {% endfor %}
    </tbody>
</table>
{% endblock %}
"""

# ------------------------------------------------------------------
PLANTILLAS["admin_agentes.html"] = r"""{% extends "admin_base.html" %}
{% block title %}Agentes{% endblock %}
{% block content %}
<h1>Agentes</h1>

<table>
    <thead>
        <tr><th>Nº</th><th>Nombre</th><th>Zona</th><th>Activo</th><th>PIN</th><th></th></tr>
    </thead>
    <tbody>
        {% for a in agentes %}
        <tr>
            <td>{{ a.num_agente }}</td>
            <td>{{ a.nombre }}</td>
            <td>{{ zonas.get(a.zona_id, '?') }}</td>
            <td>{{ '✅' if a.activo else '❌' }}</td>
            <td>{{ 'definido' if a.pin_hash else 'sin definir (1234)' }}</td>
            <td style="display:flex; gap:.4rem;">
                <form method="post" action="/admin/agentes/{{ a.id }}/reset-pin"
                      onsubmit="return confirm('¿Resetear PIN?')">
                    <button class="btn btn-secondary">Reset PIN</button>
                </form>
                <form method="post" action="/admin/agentes/{{ a.id }}/toggle-activo">
                    <button class="btn {{ 'btn-danger' if a.activo else 'btn-primary' }}">
                        {{ 'Desactivar' if a.activo else 'Activar' }}
                    </button>
                </form>
            </td>
        </tr>
        {% else %}
        <tr><td colspan="6">Sin agentes.</td></tr>
        {% endfor %}
    </tbody>
</table>
{% endblock %}
"""

# ------------------------------------------------------------------
PLANTILLAS["admin_informe.html"] = r"""{% extends "admin_base.html" %}
{% block title %}Informe{% endblock %}
{% block content %}
<h1>Informe de cambios (últimos 7 días)</h1>

<div class="card">
    <p>Cambios pendientes de volcar a Excel: <strong>{{ pendientes }}</strong></p>
    <form method="post" action="/admin/informe/forzar-volcado"
          onsubmit="return confirm('¿Marcar todos como volcados?')">
        <button class="btn btn-primary">Forzar volcado</button>
    </form>
</div>

<table>
    <thead>
        <tr>
            <th>Fecha</th><th>Solicitante</th><th>Compañero</th>
            <th>Día A</th><th>Serv. A</th><th>Día B</th><th>Serv. B</th><th>Volcado</th>
        </tr>
    </thead>
    <tbody>
        {% for f in filas %}
        <tr>
            <td>{{ f.fecha }}</td>
            <td>{{ f.solicitante.nombre if f.solicitante else '?' }}</td>
            <td>{{ f.companero.nombre if f.companero else '?' }}</td>
            <td>{{ f.dia_solicitante }}</td>
            <td>{{ f.serv_solicitante }}</td>
            <td>{{ f.dia_companero }}</td>
            <td>{{ f.serv_companero }}</td>
            <td>{{ '✅' if f.volcado else '⏳' }}</td>
        </tr>
        {% else %}
        <tr><td colspan="8">Sin cambios en los últimos 7 días.</td></tr>
        {% endfor %}
    </tbody>
</table>
{% endblock %}
"""

# ------------------------------------------------------------------
PLANTILLAS["admin_solicitudes.html"] = r"""{% extends "admin_base.html" %}
{% block title %}Solicitudes{% endblock %}
{% block content %}
<h1>Histórico de solicitudes</h1>

<table>
    <thead>
        <tr>
            <th>Fecha</th><th>Solicitante</th><th>Compañero</th>
            <th>Día A</th><th>Serv. A</th><th>Día B</th><th>Serv. B</th><th>Estado</th>
        </tr>
    </thead>
    <tbody>
        {% for f in filas %}
        <tr>
            <td>{{ f.fecha }}</td>
            <td>{{ f.solicitante.nombre if f.solicitante else '?' }}</td>
            <td>{{ f.companero.nombre if f.companero else '?' }}</td>
            <td>{{ f.dia_solicitante }}</td>
            <td>{{ f.serv_solicitante }}</td>
            <td>{{ f.dia_companero }}</td>
            <td>{{ f.serv_companero }}</td>
            <td>{{ f.estado }}</td>
        </tr>
        {% else %}
        <tr><td colspan="8">Sin solicitudes.</td></tr>
        {% endfor %}
    </tbody>
</table>
{% endblock %}
"""

# ------------------------------------------------------------------
PLANTILLAS["solicitudes_pendientes.html"] = r"""<!DOCTYPE html>
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
        th, td { padding: .55rem .7rem; text-align: left;
                 border-bottom: 1px solid #e2e8f0; font-size: .92rem; }
        th { background: #f8fafc; font-size: .8rem; color: #475569;
             text-transform: uppercase; }
        .btn { padding: .35rem .75rem; border-radius: 6px; border: none;
               cursor: pointer; font-size: .85rem; }
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
                <tr>
                    <th>Compañero</th>
                    <th>Su día</th>
                    <th>Su servicio</th>
                    <th>Tu día</th>
                    <th>Tu servicio</th>
                    <th>Acciones</th>
                </tr>
            </thead>
            <tbody>
                {% for s in pendientes %}
                <tr>
                    <td>
                        {% set sol = solicitantes.get(s.solicitante_id) %}
                        {{ sol.nombre if sol else '?' }}
                    </td>
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
                <tr>
                    <th>Compañero</th>
                    <th>Tu día</th>
                    <th>Su día</th>
                    <th>Estado</th>
                </tr>
            </thead>
            <tbody>
                {% for s in enviadas %}
                <tr>
                    <td>
                        {% set comp = companeros.get(s.companero_id) %}
                        {{ comp.nombre if comp else '?' }}
                    </td>
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

# ------------------------------------------------------------------
# Escribir con backup
# ------------------------------------------------------------------
def escribir_plantillas():
    creados, respaldados = [], []
    for nombre, contenido in PLANTILLAS.items():
        destino = os.path.join(TPL_DIR, nombre)
        if os.path.exists(destino):
            os.makedirs(BACKUP_DIR, exist_ok=True)
            shutil.copy2(destino, os.path.join(BACKUP_DIR, nombre))
            respaldados.append(nombre)
        with open(destino, "w", encoding="utf-8") as f:
            f.write(contenido)
        creados.append(nombre)
    return creados, respaldados


def crear_zip():
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre in PLANTILLAS:
            ruta = os.path.join(TPL_DIR, nombre)
            z.write(ruta, arcname=f"app/templates/{nombre}")
    return ZIP_PATH


if __name__ == "__main__":
    print("📁 Plantillas destino:", TPL_DIR)
    creados, respaldados = escribir_plantillas()
    print(f"\n✅ {len(creados)} plantillas escritas:")
    for n in creados:
        print("   -", n)

    if respaldados:
        print(f"\n🗂️  Backup de las que ya existían en: {BACKUP_DIR}")
        for n in respaldados:
            print("   -", n)

    zip_path = crear_zip()
    print(f"\n📦 ZIP creado: {zip_path}")
    print("\n👉 Reinicia uvicorn o espera al autoreload y prueba:")
    print("   http://127.0.0.1:8000/admin/login")
    print("   Usuario: 2354  |  Contraseña: Admin2026!")