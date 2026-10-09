"""
Layout de un Excel de cuadrantes.

Fila 1 (o fila_inicio_datos-1): cabecera.
Datos desde `fila_inicio_datos` (1-based).

Columnas de identificación por fila:
    col_identificador -> AE6 (grupo al que pertenece el trabajador)
    col_nombre        -> nombre del trabajador
    col_cf            -> carnet ferroviario

Columnas de servicios:
    col_servicios -> primera columna con el turno del día 1
    gap           -> nº de columnas vacías entre servicio y servicio
                     (gap=1 -> se salta 1 -> paso=2)
                     (gap=4 -> se saltan 4 -> paso=5)
"""

from dataclasses import dataclass


def col_letra_a_indice(letra: str) -> int:
    letra = letra.strip().upper()
    if not letra:
        raise ValueError("Columna vacía")
    n = 0
    for c in letra:
        if not ("A" <= c <= "Z"):
            raise ValueError(f"Columna inválida: {letra!r}")
        n = n * 26 + (ord(c) - ord("A") + 1)
    return n - 1


def col_indice_a_letra(idx: int) -> str:
    if idx < 0:
        raise ValueError(f"Índice de columna negativo: {idx}")
    s = ""
    idx += 1
    while idx:
        idx, r = divmod(idx - 1, 26)
        s = chr(65 + r) + s
    return s


@dataclass
class LayoutExcel:
    # Columnas de identificación (fijas, una por fila)
    col_identificador: str = "A"   # AE6
    col_nombre: str = "B"
    col_cf: str = "C"

    # Fila de inicio de datos
    fila_inicio_datos: int = 2

    # Servicios / turnos
    col_servicios: str = "E"
    gap: int = 1                   # columnas vacías entre servicios

    def __post_init__(self) -> None:
        for nombre, letra in (
            ("col_identificador", self.col_identificador),
            ("col_nombre", self.col_nombre),
            ("col_cf", self.col_cf),
            ("col_servicios", self.col_servicios),
        ):
            try:
                col_letra_a_indice(letra)
            except ValueError as e:
                raise ValueError(f"{nombre}={letra!r} no es válida: {e}")
        if self.fila_inicio_datos < 1:
            raise ValueError("fila_inicio_datos debe ser >= 1")
        if self.gap < 0:
            raise ValueError("gap debe ser >= 0")

    # ---------------- servicios/turnos ----------------

    @property
    def paso_columnas(self) -> int:
        return self.gap + 1

    def columna_servicio(self, i: int) -> str:
        """Letra de la columna del servicio i (0-based)."""
        if i < 0:
            raise ValueError("Índice de servicio negativo")
        base = col_letra_a_indice(self.col_servicios)
        return col_indice_a_letra(base + i * self.paso_columnas)

    def celda_servicio(self, i: int) -> str:
        return f"{self.columna_servicio(i)}{self.fila_inicio_datos}"

    def primeros_servicios(self, n: int = 10) -> list[str]:
        return [self.columna_servicio(i) for i in range(n)]

    # ---------------- columnas de identificación ----------------

    def celda_identificador(self, fila: int) -> str:
        return f"{self.col_identificador}{fila}"

    def celda_nombre(self, fila: int) -> str:
        return f"{self.col_nombre}{fila}"

    def celda_cf(self, fila: int) -> str:
        return f"{self.col_cf}{fila}"

    # ---------------- compatibilidad con el nombre antiguo ---------

    # Alias para no romper llamadas existentes que usen .columna_turno()
    def columna_turno(self, i: int) -> str:
        return self.columna_servicio(i)