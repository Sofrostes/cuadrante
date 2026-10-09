"""
Corrige el catálogo de servicios: 93 y 94 no son cambiables.
"""

import re
from app.db.conexion import SessionLocal
from app.db.modelos import Servicio

# Servicios que NUNCA se cambian (aunque empiecen por dígito)
BLOQUEADOS = {"93", "94"}


def es_cambiable(codigo: str) -> bool:
    if not codigo:
        return False
    c = codigo.strip().upper()
    if c in BLOQUEADOS:
        return False
    # Acepta: 1, 2, 3F, 3S, 3FN, 3SN, 12, 12F, 12S, 15S, 20F...
    return bool(re.match(r"^\d{1,2}(F|S|N|FN|SN)?$", c))


def corregir():
    db = SessionLocal()
    try:
        todos = db.query(Servicio).all()
        cambios = 0
        for s in todos:
            nuevo = es_cambiable(s.codigo)
            if s.cambiable != nuevo:
                print(f"   {s.codigo:<6} : {s.cambiable} -> {nuevo}")
                s.cambiable = nuevo
                cambios += 1
        db.commit()
        print(f"\n✅ {cambios} servicios corregidos")

        # Resumen final
        camb = sorted([s.codigo for s in db.query(Servicio).filter_by(cambiable=True).all()])
        ncamb = sorted([s.codigo for s in db.query(Servicio).filter_by(cambiable=False).all()])
        print(f"\n   Cambiables    ({len(camb)}): {camb}")
        print(f"\n   No cambiables ({len(ncamb)}): {ncamb}")
    finally:
        db.close()


if __name__ == "__main__":
    corregir()