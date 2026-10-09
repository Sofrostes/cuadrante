"""
Importador de la hoja MAYO 2026 a la base de datos.
Solo importa zonas AE6, AE7 y AE8.
"""

import re
from datetime import date
from pathlib import Path

from openpyxl import load_workbook

from app.db.conexion import SessionLocal, crear_tablas
from app.db.modelos import Zona, Agente, Servicio, Cuadrante

# ----------------------------------------------------------------------
# CONFIGURACIÓN
# ----------------------------------------------------------------------

RUTA_EXCEL = Path("datos") / "mayo2026.xlsx"
HOJA = "MAYO 2026"
MES = 5
ANIO = 2026

# Rangos de filas de cada zona (donde están los datos, sin contar cabecera)
# La fila de cabecera COD./AGENTE está UNA fila antes de INICIO
ZONAS = {
    "AE6": {
        "nombre": "ZONA 6 AGENTE DE ESTACIONES DE ATENCION AL CLIENTE",
        "inicio": 140,   # primer agente
        "fin": 173,      # último agente
    },
    "AE7": {
        "nombre": "ZONA 7 AGENTE DE ESTACIONES DE ATENCION AL CLIENTE",
        "inicio": 196,
        "fin": 237,
    },
    "AE8": {
        "nombre": "ZONA 8 AGENTE DE ESTACIONES DE ATENCION AL CLIENTE",
        "inicio": 262,
        "fin": 291,
    },
}

COL_ZONA = 1        # A
COL_NUM_AGENTE = 4  # D
COL_NOMBRE = 5      # E
COL_DIA_1 = 6       # F  (día 1)
COL_DIA_2 = 8       # H  (día 2)
SALTO_DIAS = 2      # F -> H -> J -> ...
NUM_DIAS = 31


# ----------------------------------------------------------------------
# UTILIDADES
# ----------------------------------------------------------------------

def es_num_agente_valido(valor) -> bool:
    """True si es un nº de agente real (entero positivo)."""
    if valor is None:
        return False
    s = str(valor).strip()
    if not s:
        return False
    if not s.isdigit():
        return False
    return int(s) > 0


def es_nombre_agente_valido(nombre: str) -> bool:
    """Descarta VACANTE, DESPLAZADO, vacíos, etc."""
    if not nombre:
        return False
    n = str(nombre).strip().upper()
    if not n:
        return False
    for palabra_prohibida in ["VACANTE", "DESPLAZADO"]:
        if palabra_prohibida in n:
            return False
    return True


def es_servicio_cambiable(codigo: str) -> bool:
    """
    True si el servicio es cambiable.
    Regla: empieza por dígito (1, 2, 3F, 12S, 3FN, 15, 16F...).
    Todo lo demás (D, E, VC, LC, FO, SP, 93, 94...) NO.
    """
    if codigo is None:
        return False
    s = str(codigo).strip()
    if not s:
        return False
    return bool(re.match(r"^\d", s))


def limpiar_valor(v):
    """Convierte a string limpio o None."""
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


# ----------------------------------------------------------------------
# IMPORTACIÓN
# ----------------------------------------------------------------------

def importar():
    print("🔧 Creando tablas si no existen...")
    crear_tablas()

    print(f"📂 Abriendo {RUTA_EXCEL} ...")
    wb = load_workbook(RUTA_EXCEL, data_only=True)
    hoja = wb[HOJA]

    db = SessionLocal()
    try:
        # 1) Zonas
        print("\n📍 Creando zonas...")
        zonas_db = {}
        for codigo, info in ZONAS.items():
            zona = db.query(Zona).filter_by(codigo=codigo).first()
            if not zona:
                zona = Zona(
                    codigo=codigo,
                    nombre=info["nombre"],
                    fila_inicio=info["inicio"],
                    fila_fin=info["fin"],
                )
                db.add(zona)
                db.flush()
                print(f"   + {codigo}: {info['nombre']}")
            else:
                # Actualizamos filas
                zona.fila_inicio = info["inicio"]
                zona.fila_fin = info["fin"]
                print(f"   = {codigo} (ya existía)")
            zonas_db[codigo] = zona

        # 2) Servicios (los iremos descubriendo)
        print("\n🎫 Descubriendo servicios...")
        servicios_db = {s.codigo: s for s in db.query(Servicio).all()}

        def registrar_servicio(codigo: str):
            if codigo in servicios_db:
                return
            s = Servicio(
                codigo=codigo,
                descripcion=None,
                cambiable=es_servicio_cambiable(codigo),
            )
            db.add(s)
            servicios_db[codigo] = s

        # 3) Agentes y cuadrante
        print("\n👥 Importando agentes y cuadrante...\n")
        total_agentes = 0
        total_servicios = 0
        descartados = []

        for codigo_zona, info in ZONAS.items():
            zona = zonas_db[codigo_zona]
            print(f"   --- {codigo_zona} (filas {info['inicio']}–{info['fin']}) ---")

            for fila in range(info["inicio"], info["fin"] + 1):
                num_agente_raw = hoja.cell(fila, COL_NUM_AGENTE).value
                nombre_raw = hoja.cell(fila, COL_NOMBRE).value

                # Validaciones
                if not es_num_agente_valido(num_agente_raw):
                    continue
                if not es_nombre_agente_valido(nombre_raw):
                    descartados.append((fila, num_agente_raw, nombre_raw))
                    continue

                num_agente = str(int(num_agente_raw))
                nombre = str(nombre_raw).strip()

                # ¿Existe ya el agente?
                agente = db.query(Agente).filter_by(num_agente=num_agente).first()
                if agente:
                    agente.nombre = nombre
                    agente.zona_id = zona.id
                    agente.fila_excel = fila
                    agente.activo = True
                else:
                    agente = Agente(
                        num_agente=num_agente,
                        nombre=nombre,
                        zona_id=zona.id,
                        fila_excel=fila,
                        activo=True,
                    )
                    db.add(agente)
                    db.flush()
                    total_agentes += 1

                print(f"      ✓ F{fila:>3} | {num_agente:>6} | {nombre}")

                # 4) Cuadrante del mes
                for dia in range(1, NUM_DIAS + 1):
                    col = COL_DIA_1 + (dia - 1) * SALTO_DIAS
                    if col > hoja.max_column:
                        break
                    valor = limpiar_valor(hoja.cell(fila, col).value)
                    if valor is None:
                        continue
                    registrar_servicio(valor)

                    # ¿Ya existe registro?
                    reg = (
                        db.query(Cuadrante)
                        .filter_by(agente_id=agente.id, mes=MES, anio=ANIO, dia=dia)
                        .first()
                    )
                    if reg:
                        reg.servicio = valor
                        reg.col_excel = col
                    else:
                        db.add(
                            Cuadrante(
                                agente_id=agente.id,
                                mes=MES,
                                anio=ANIO,
                                dia=dia,
                                servicio=valor,
                                col_excel=col,
                            )
                        )
                        total_servicios += 1

        db.commit()

        # 5) Resumen
        print("\n" + "=" * 60)
        print("✅ IMPORTACIÓN COMPLETA")
        print("=" * 60)
        print(f"   Zonas creadas/actualizadas : {len(zonas_db)}")
        print(f"   Agentes nuevos             : {total_agentes}")
        print(f"   Servicios en cuadrante     : {total_servicios}")
        print(f"   Catálogo de servicios      : {len(servicios_db)}")
        print(f"   Filas descartadas          : {len(descartados)}")
        if descartados:
            print("\n   Descartados (primeros 10):")
            for f, n, nom in descartados[:10]:
                print(f"      F{f:>3} | {n!r} | {nom!r}")

        # Listado de servicios
        print("\n   Catálogo de servicios:")
        cambiables = [s for s in servicios_db.values() if s.cambiable]
        no_cambiables = [s for s in servicios_db.values() if not s.cambiable]
        print(f"      Cambiables    ({len(cambiables)}): {sorted(s.codigo for s in cambiables)}")
        print(f"      No cambiables ({len(no_cambiables)}): {sorted(s.codigo for s in no_cambiables)}")

    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    importar()