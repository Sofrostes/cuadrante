from dataclasses import dataclass


def col_letra_a_indice(letra: str) -> int:
    letra = (letra or "").strip().upper()
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
        raise ValueError(f"Índice negativo: {idx}")
    s = ""
    idx += 1
    while idx:
        idx, r = divmod(idx - 1, 26)
        s = chr(65 + r) + s
    return s


@dataclass
class LayoutExcel:
    col_control: str = "A"
    col_nombre: str = "B"
    col_cf: str = "C"
    fila_inicio_datos: int = 2
    col_servicios: str = "E"
    gap: int = 1

    def __post_init__(self) -> None:
        for nombre, letra in (
            ("col_control", self.col_control),
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

    @property
    def paso_columnas(self) -> int:
        return self.gap + 1

    @property
    def col_identificador(self) -> str:
        return self.col_control

    def columna_servicio(self, i: int) -> str:
        if i < 0:
            raise ValueError("Índice negativo")
        base = col_letra_a_indice(self.col_servicios)
        return col_indice_a_letra(base + i * self.paso_columnas)

    def columna_turno(self, i: int) -> str:
        return self.columna_servicio(i)

    def celda_servicio(self, i: int) -> str:
        return f"{self.columna_servicio(i)}{self.fila_inicio_datos}"

    def primeros_servicios(self, n: int = 10) -> list[str]:
        return [self.columna_servicio(i) for i in range(n)]

    def celda_identificador(self, fila: int) -> str:
        return f"{self.col_control}{fila}"

    def celda_nombre(self, fila: int) -> str:
        return f"{self.col_nombre}{fila}"

    def celda_cf(self, fila: int) -> str:
        return f"{self.col_cf}{fila}"