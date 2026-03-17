"""
Repositorio de Devolucion: único responsable del SQL relacionado a devoluciones.
"""
from src.core.database import get_connection
from src.models.devolucion import Devolucion


class DevolucionRepository:

    def find_by_venta(self, venta_id: int) -> list[Devolucion]:
        """Retorna todas las devoluciones de una venta, indexadas por venta_item_id."""
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM devoluciones WHERE venta_id = ? ORDER BY id",
                (venta_id,),
            ).fetchall()
            return [Devolucion.from_row(r) for r in rows]
        finally:
            conn.close()

    def find_by_item(self, venta_item_id: int) -> Devolucion | None:
        """Retorna la devolución de un ítem, o None si no tiene."""
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM devoluciones WHERE venta_item_id = ? LIMIT 1",
                (venta_item_id,),
            ).fetchone()
            return Devolucion.from_row(row) if row else None
        finally:
            conn.close()

    def create(self, d: Devolucion) -> int:
        """Inserta la devolución y retorna el id generado."""
        conn = get_connection()
        try:
            cur = conn.execute(
                """INSERT INTO devoluciones
                   (venta_item_id, venta_id, cantidad_devuelta, cantidad_a_stock,
                    monto_devuelto, fecha, observacion)
                   VALUES (?,?,?,?,?,?,?)""",
                (d.venta_item_id, d.venta_id, d.cantidad_devuelta, d.cantidad_a_stock,
                 d.monto_devuelto, d.fecha, d.observacion),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def reintegrar_stock(self, variante_id: int, cantidad: int) -> None:
        """Suma `cantidad` al stock de la variante indicada."""
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE producto_variantes SET stock = stock + ? WHERE id = ?",
                (cantidad, variante_id),
            )
            conn.commit()
        finally:
            conn.close()


devolucion_repository = DevolucionRepository()
