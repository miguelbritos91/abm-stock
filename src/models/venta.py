"""
Modelos de dominio: Venta, VentaItem, Pago.
Estructuras de datos puras — no conocen SQL ni UI.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.devolucion import Devolucion


@dataclass
class VentaItem:
    """Una línea de producto dentro de una venta."""
    producto_id: int
    nombre_producto: str
    precio_unitario: float
    cantidad: int
    subtotal: float = 0.0
    id: Optional[int] = None
    venta_id: Optional[int] = None
    variante_id: Optional[int] = None  # FK a producto_variantes
    devolucion: Optional["Devolucion"] = field(default=None, compare=False)

    def __post_init__(self):
        self.subtotal = round(self.precio_unitario * self.cantidad, 2)

    @classmethod
    def from_row(cls, row) -> "VentaItem":
        keys = row.keys() if hasattr(row, "keys") else []
        return cls(
            id=row["id"],
            venta_id=row["venta_id"],
            producto_id=row["producto_id"],
            nombre_producto=row["nombre_producto"] or "",
            precio_unitario=float(row["precio_unitario"] or 0),
            cantidad=int(row["cantidad"] or 1),
            subtotal=float(row["subtotal"] or 0),
            variante_id=row["variante_id"] if "variante_id" in keys else None,
        )


@dataclass
class Pago:
    """Pago asociado a una venta."""
    venta_id: int
    monto: float
    tipo: str                    # "efectivo" | "transferencia" | "tarjeta"
    fecha: str                   # ISO: YYYY-MM-DD
    id: Optional[int] = None

    @classmethod
    def from_row(cls, row) -> "Pago":
        return cls(
            id=row["id"],
            venta_id=row["venta_id"],
            monto=float(row["monto"] or 0),
            tipo=row["tipo"] or "efectivo",
            fecha=row["fecha"] or "",
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "venta_id": self.venta_id,
            "monto": self.monto,
            "tipo": self.tipo,
            "fecha": self.fecha,
        }


@dataclass
class Venta:
    """Cabecera de una venta."""
    estado: str = "abierta"      # "abierta" | "cerrada"
    id: Optional[int] = None
    cliente_id: Optional[int] = None
    nombre_cliente: str = ""     # desnormalizado para display rápido
    fecha_apertura: str = ""     # YYYY-MM-DD HH:MM:SS
    fecha_cierre: str = ""
    items: list = field(default_factory=list)     # list[VentaItem]
    pagos: list = field(default_factory=list)     # list[Pago]

    @property
    def total(self) -> float:
        return round(sum(i.subtotal for i in self.items), 2)

    @property
    def total_devoluciones(self) -> float:
        return round(
            sum(i.devolucion.monto_devuelto for i in self.items if i.devolucion), 2
        )

    @property
    def total_ajustado(self) -> float:
        return round(self.total - self.total_devoluciones, 2)

    @property
    def total_pagado(self) -> float:
        return round(sum(p.monto for p in self.pagos), 2)

    @property
    def saldo(self) -> float:
        return round(self.total_ajustado - self.total_pagado, 2)

    @classmethod
    def from_row(cls, row) -> "Venta":
        return cls(
            id=row["id"],
            cliente_id=row["cliente_id"],
            nombre_cliente=row["nombre_cliente"] or "",
            estado=row["estado"] or "abierta",
            fecha_apertura=row["fecha_apertura"] or "",
            fecha_cierre=row["fecha_cierre"] or "",
        )
