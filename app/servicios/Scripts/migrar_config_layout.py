"""
Migra las claves antiguas de layout a las nuevas.
Idempotente: si ya existe la clave nueva, no la toca.

  excel.fichero + excel.ruta        -> excel.ruta (ruta completa)
  excel.col_inicio_turnos           -> excel.col_servicios
  excel.paso_columnas (2)           -> excel.gap (1)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import SessionLocal, engine, Base
from app.modelos.configuracion import Configuracion  # noqa
from app.servicios import configuracion as cfg


def main() -> int:
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        # 1) ruta completa
        if cfg.get_config(db, cfg.K_RUTA) in (None, ""):
            base = cfg.get_config(db, "excel.ruta", "") or ""
            fichero = cfg.get_config(db, "excel.fichero", "") or ""
            if base and fichero:
                completa = str(Path(base) / fichero)
                cfg.set_config(db, cfg.K_RUTA, completa)
                print(f"✓ excel.ruta = {completa!r}")

        # 2) col_servicios
        if cfg.get_config(db, cfg.K_COL_SERVICIOS) in (None, ""):
            viejo = cfg.get_config(db, "excel.col_inicio_turnos", "")
            if viejo:
                cfg.set_config(db, cfg.K_COL_SERVICIOS, viejo)
                print(f"✓ excel.col_servicios = {viejo!r}")

        # 3) gap = paso - 1
        if cfg.get_config(db, cfg.K_GAP) in (None, ""):
            paso = cfg.get_config(db, "excel.paso_columnas", "")
            if paso:
                try:
                    gap = max(0, int(paso) - 1)
                    cfg.set_config(db, cfg.K_GAP, str(gap))
                    print(f"✓ excel.gap = {gap}")
                except ValueError:
                    pass

        # 4) defaults de columnas nuevas si faltan
        for clave, default in (
            (cfg.K_COL_ID, "A"),
            (cfg.K_COL_NOMBRE, "B"),
            (cfg.K_COL_CF, "C"),
            (cfg.K_FILA_INI, "2"),
        ):
            if cfg.get_config(db, clave) in (None, ""):
                cfg.set_config(db, clave, default)
                print(f"✓ {clave} = {default!r}")

    print("\nMigración terminada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())