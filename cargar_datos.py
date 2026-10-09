"""
Script de carga inicial de datos de prueba.
Ejecutar UNA vez: python cargar_datos.py
"""
from app.db.conexion import SessionLocal, crear_tablas
from app.db.modelos import Zona, Agente, Servicio, Cuadrante

crear_tablas()
db = SessionLocal()

try:
    # --- Zonas (ya las tienes creadas, esto no hará nada si ya existen) ---
    if db.query(Zona).count() == 0:
        db.add_all([
            Zona(codigo="Z1", nombre="Zona 1", fila_inicio=3,  fila_fin=10),
            Zona(codigo="Z2", nombre="Zona 2", fila_inicio=11, fila_fin=18),
        ])
        db.commit()
        print("✅ Zonas creadas")
    else:
        print("ℹ️  Zonas ya existían, no se tocan")

    # --- Servicios ---
    if db.query(Servicio).count() == 0:
        db.add_all([
            Servicio(codigo="M", descripcion="Mañana",     cambiable=True),
            Servicio(codigo="T", descripcion="Tarde",      cambiable=True),
            Servicio(codigo="N", descripcion="Noche",      cambiable=True),
            Servicio(codigo="L", descripcion="Libre",      cambiable=False),
            Servicio(codigo="V", descripcion="Vacaciones", cambiable=False),
        ])
        db.commit()
        print("✅ Servicios creados")
    else:
        print("ℹ️  Servicios ya existían, no se tocan")

    # --- Agentes ---
    if db.query(Agente).count() == 0:
        z1 = db.query(Zona).filter_by(codigo="Z1").first()
        z2 = db.query(Zona).filter_by(codigo="Z2").first()

        db.add_all([
            Agente(num_agente="1001", nombre="Ana García",   zona_id=z1.id, fila_excel=1, activo=True),
            Agente(num_agente="1002", nombre="Luis Pérez",   zona_id=z1.id, fila_excel=2, activo=True),
            Agente(num_agente="1003", nombre="Marta Ruiz",   zona_id=z1.id, fila_excel=3, activo=True),
            Agente(num_agente="2001", nombre="Carlos López", zona_id=z2.id, fila_excel=1, activo=True),
            Agente(num_agente="2002", nombre="Elena Díaz",   zona_id=z2.id, fila_excel=2, activo=True),
        ])
        db.commit()
        print("✅ Agentes creados")
    else:
        print("ℹ️  Agentes ya existían, no se tocan")

    # --- Cuadrante de prueba (mayo 2026) ---
    # Si ya hay cuadrante para el mes, lo saltamos
    if db.query(Cuadrante).filter_by(mes=5, anio=2026).count() == 0:
        agentes = db.query(Agente).all()
        # Mapa día → columna en el Excel (ajústalo tú a tu Excel real)
        # Ejemplo: día 1 está en la columna 4, día 2 en la 5, ...
        dia_a_col = {d: d + 3 for d in range(1, 32)}

        # Patrón de ejemplo: alternamos M, T, N, L
        patron = ["M", "T", "N", "L"]

        for ag in agentes:
            for d in range(1, 32):
                db.add(Cuadrante(
                    agente_id=ag.id,
                    mes=5, anio=2026, dia=d,
                    servicio=patron[(d + ag.id) % len(patron)],
                    col_excel=dia_a_col[d],
                ))
        db.commit()
        print("✅ Cuadrante de mayo 2026 creado (31 días × 5 agentes)")
    else:
        print("ℹ️  Cuadrante de mayo 2026 ya existía, no se toca")

    # --- Resumen final ---
    print("\n📊 Estado actual:")
    print(f"   Zonas:      {db.query(Zona).count()}")
    print(f"   Servicios:  {db.query(Servicio).count()}")
    print(f"   Agentes:    {db.query(Agente).count()}")
    print(f"   Cuadrante:  {db.query(Cuadrante).count()} filas")

    print("\n🔑 Prueba a loguearte con:")
    for a in db.query(Agente).all():
        print(f"   {a.num_agente}  (PIN inicial: 1234)  → {a.nombre}")

finally:
    db.close()