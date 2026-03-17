"""
Modelos de dominio: Producto, ProductoVariante, ProductoImagen.

Estructuras de datos puras — no saben nada de SQL ni de la UI.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProductoVariante:
    """Combinación talla + color con su stock asociado a un producto."""
    talla: str
    color: str
    stock: int = 0
    id: Optional[int] = None
    producto_id: Optional[int] = None

    @classmethod
    def from_row(cls, row) -> "ProductoVariante":
        return cls(
            id=row["id"],
            producto_id=row["producto_id"],
            talla=row["talla"] or "",
            color=row["color"] or "",
            stock=int(row["stock"] or 0),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "producto_id": self.producto_id,
            "talla": self.talla,
            "color": self.color,
            "stock": self.stock,
        }


@dataclass
class ProductoImagen:
    """Imagen asociada a un producto, identificada por UUID en el filesystem."""
    filename: str
    orden: int = 0
    id: Optional[int] = None
    producto_id: Optional[int] = None

    @classmethod
    def from_row(cls, row) -> "ProductoImagen":
        return cls(
            id=row["id"],
            producto_id=row["producto_id"],
            filename=row["filename"] or "",
            orden=int(row["orden"] or 0),
        )


@dataclass
class Producto:
    """Producto del stock con variantes (talla/color/stock) e imágenes múltiples."""

    codigo: str
    nombre: str
    id: Optional[int] = None
    descripcion: str = ""
    precio_costo: float = 0.0
    porcentaje_ganancia: float = 0.0
    precio_unitario: float = 0.0
    categoria: str = ""
    variantes: list[ProductoVariante] = field(default_factory=list)
    imagenes: list[ProductoImagen] = field(default_factory=list)

    # ── Lógica de negocio del modelo ────────────────────────────────────

    def calcular_precio_unitario(self) -> float:
        """Precio de costo + margen de ganancia porcentual."""
        return round(
            self.precio_costo + self.precio_costo * self.porcentaje_ganancia / 100,
            2,
        )

    @property
    def stock_total(self) -> int:
        """Suma del stock de todas las variantes."""
        return sum(v.stock for v in self.variantes)

    @property
    def imagen_principal(self) -> str:
        """Filename de la primera imagen (orden 0), o '' si no hay imágenes."""
        if not self.imagenes:
            return ""
        sorted_imgs = sorted(self.imagenes, key=lambda i: i.orden)
        return sorted_imgs[0].filename

    # ── Constructores alternativos ───────────────────────────────────────

    @classmethod
    def from_row(cls, row) -> "Producto":
        """Construye un Producto desde una sqlite3.Row (sin variantes ni imágenes)."""
        return cls(
            id=row["id"],
            codigo=row["codigo"],
            nombre=row["nombre"],
            descripcion=row["descripcion"] or "",
            precio_costo=float(row["precio_costo"] or 0),
            porcentaje_ganancia=float(row["porcentaje_ganancia"] or 0),
            precio_unitario=float(row["precio_unitario"] or 0),
            categoria=row["categoria"] or "",
        )

    @classmethod
    def from_dict(cls, data: dict) -> "Producto":
        """Construye un Producto desde un diccionario (ej: formulario UI)."""
        return cls(
            id=data.get("id"),
            codigo=data.get("codigo", ""),
            nombre=data.get("nombre", ""),
            descripcion=data.get("descripcion", ""),
            precio_costo=float(data.get("precio_costo", 0)),
            porcentaje_ganancia=float(data.get("porcentaje_ganancia", 0)),
            precio_unitario=float(data.get("precio_unitario", 0)),
            categoria=data.get("categoria", ""),
        )
