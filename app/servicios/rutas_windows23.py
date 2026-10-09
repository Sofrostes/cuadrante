"""
Traducción de rutas Windows entre 'Z:\\...' y UNC '\\\\SERVIDOR\\recurso\\...'.

Motivación: los servicios Windows (uvicorn) NO heredan las unidades
mapeadas del usuario interactivo. Guardar siempre UNC evita
FileNotFoundError en el contexto del servicio.
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Optional


_RE_UNC = re.compile(r"\\\\[^\\\s]+\\[^\\\s]+")


def _net_use(letra: str) -> Optional[str]:
    try:
        return subprocess.check_output(
            ["cmd", "/c", "net", "use", letra],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=5,
            encoding="cp850",
            errors="replace",
        )
    except Exception:
        return None


def letra_a_unc(ruta: str) -> str:
    if not ruta:
        return ruta
    ruta = ruta.strip()

    p = Path(ruta)
    drive = p.drive
    if not drive or len(drive) != 2 or drive[1] != ":":
        return ruta  # ya es UNC, relativa o no-Windows

    salida = _net_use(drive)
    if not salida:
        return ruta

    m = _RE_UNC.search(salida)
    if not m:
        return ruta

    unc_base = m.group(0).rstrip("\\")
    resto = str(p)[len(drive):].lstrip("\\/").replace("/", "\\")
    return f"{unc_base}\\{resto}" if resto else unc_base


def normalizar_ruta(ruta: str) -> str:
    return letra_a_unc(ruta)


def diagnostico() -> dict:
    unidades = []
    try:
        out = subprocess.check_output(
            ["cmd", "/c", "net", "use"],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=5,
            encoding="cp850",
            errors="replace",
        )
        for linea in out.splitlines():
            linea = linea.strip()
            if linea and (":" in linea[:3] or linea.startswith("\\\\")):
                unidades.append(linea)
    except Exception as e:
        unidades.append(f"(error leyendo net use: {e})")

    return {
        "usuario_servicio": os.environ.get("USERNAME") or os.environ.get("USER") or "?",
        "dominio": os.environ.get("USERDOMAIN", ""),
        "computadora": os.environ.get("COMPUTERNAME", ""),
        "unidades": unidades,
    }