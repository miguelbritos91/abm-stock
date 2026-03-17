"""
Modelo de dominio: Devolucion.
Representa la devolución (total o parcial) de un ítem de venta.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Devolucion:
    """Devolución asociada a un ítem de venta."""
    venta_item_id: int
    venta_id: int
    cantidad_devuelta: int          # unidades devueltas por el cliente
    cantidad_a_stock: int = 0       # de esas, cuántas vuelven al inventario
    monto_devuelto: float = 0.0     # precio_unitario * cantidad_devuelta
    fecha: str = ""                 # YYYY-MM-DD
    observacion: str = ""
    id: Optional[int] = None

    @classmethod
    def from_row(cls, row) -> "Devolucion":
        return cls(
            id=row["id"],
            venta_item_id=row["venta_item_id"],
            venta_id=row["venta_id"],
            cantidad_devuelta=int(row["cantidad_devuelta"] or 0),
            cantidad_a_stock=int(row["cantidad_a_stock"] or 0),
            monto_devuelto=float(row["monto_devuelto"] or 0),
            fecha=row["fecha"] or "",
            observacion=row["observacion"] or "",
        )
