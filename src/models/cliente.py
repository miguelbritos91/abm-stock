"""
Modelo de dominio: Cliente.
Estructura de datos pura — no conoce SQL ni UI.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Cliente:
    nombre: str
    telefono: str
    id: Optional[int] = None
    cuit_dni: str = ""
    direccion: str = ""
    email: str = ""
    fecha_nacimiento: str = ""   # almacenado como texto ISO: YYYY-MM-DD
    sexo: str = ""               # "M" | "F" | "Otro" | ""

    @classmethod
    def from_row(cls, row) -> "Cliente":
        return cls(
            id=row["id"],
            cuit_dni=row["cuit_dni"] or "",
            nombre=row["nombre"] or "",
            telefono=row["telefono"] or "",
            direccion=row["direccion"] or "",
            email=row["email"] or "",
            fecha_nacimiento=row["fecha_nacimiento"] or "",
            sexo=row["sexo"] or "",
        )

    def to_dict(self) -> dict:
        return {
            "id":               self.id,
            "cuit_dni":         self.cuit_dni,
            "nombre":           self.nombre,
            "telefono":         self.telefono,
            "direccion":        self.direccion,
            "email":            self.email,
            "fecha_nacimiento": self.fecha_nacimiento,
            "sexo":             self.sexo,
        }
