"""
Repositorio de Venta y Pago: único responsable del SQL.
"""
from src.core.database import get_connection
from src.models.venta import Venta, VentaItem, Pago
from src.models.devolucion import Devolucion


class VentaRepository:

    # ── Helpers ───────────────────────────────────────────────────────────

    def _load_items(self, conn, venta_id: int) -> list[VentaItem]:
        rows = conn.execute(
            "SELECT * FROM venta_items WHERE venta_id = ? ORDER BY id",
            (venta_id,),
        ).fetchall()
        items = [VentaItem.from_row(r) for r in rows]
        # Adjuntar devoluciones
        dev_rows = conn.execute(
            "SELECT * FROM devoluciones WHERE venta_id = ?",
            (venta_id,),
        ).fetchall()
        dev_by_item = {r["venta_item_id"]: Devolucion.from_row(r) for r in dev_rows}
        for item in items:
            item.devolucion = dev_by_item.get(item.id)
        return items

    def _load_pagos(self, conn, venta_id: int) -> list[Pago]:
        rows = conn.execute(
            "SELECT * FROM pagos WHERE venta_id = ? ORDER BY fecha, id",
            (venta_id,),
        ).fetchall()
        return [Pago.from_row(r) for r in rows]

    def _enrich(self, conn, ventas: list[Venta]) -> list[Venta]:
        for v in ventas:
            v.items = self._load_items(conn, v.id)
            v.pagos = self._load_pagos(conn, v.id)
        return ventas

    # ── Consultas ─────────────────────────────────────────────────────────

    def find_abierta(self) -> Venta | None:
        """Retorna la única venta abierta (si existe)."""
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM ventas WHERE estado = 'abierta' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if not row:
                return None
            v = Venta.from_row(row)
            v.items = self._load_items(conn, v.id)
            v.pagos = self._load_pagos(conn, v.id)
            return v
        finally:
            conn.close()

    def find_by_id(self, venta_id: int) -> Venta | None:
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM ventas WHERE id = ?", (venta_id,)
            ).fetchone()
            if not row:
                return None
            v = Venta.from_row(row)
            v.items = self._load_items(conn, v.id)
            v.pagos = self._load_pagos(conn, v.id)
            return v
        finally:
            conn.close()

    def find_historial(
        self,
        search: str = "",
        fecha_desde: str = "",
        fecha_hasta: str = "",
        offset: int = 0,
        limit: int = 25,
    ) -> list[Venta]:
        conn = get_connection()
        try:
            where, params = self._historial_where(search, fecha_desde, fecha_hasta)
            rows = conn.execute(
                f"SELECT * FROM ventas {where} ORDER BY fecha_apertura DESC LIMIT ? OFFSET ?",
                params + [limit, offset],
            ).fetchall()
            return self._enrich(conn, [Venta.from_row(r) for r in rows])
        finally:
            conn.close()

    def count_historial(
        self,
        search: str = "",
        fecha_desde: str = "",
        fecha_hasta: str = "",
    ) -> int:
        conn = get_connection()
        try:
            where, params = self._historial_where(search, fecha_desde, fecha_hasta)
            return conn.execute(
                f"SELECT COUNT(*) AS n FROM ventas {where}", params
            ).fetchone()["n"]
        finally:
            conn.close()

    def _historial_where(self, search, fecha_desde, fecha_hasta):
        clauses, params = ["estado = 'cerrada'"], []
        if search:
            clauses.append("nombre_cliente LIKE ?")
            params.append(f"%{search}%")
        if fecha_desde:
            clauses.append("fecha_apertura >= ?")
            params.append(fecha_desde)
        if fecha_hasta:
            clauses.append("fecha_apertura <= ?")
            params.append(fecha_hasta + " 23:59:59")
        return ("WHERE " + " AND ".join(clauses)) if clauses else "", params

    # ── Mutaciones ────────────────────────────────────────────────────────

    def create(self) -> int:
        """Crea una venta vacía en estado abierta y retorna su id."""
        conn = get_connection()
        try:
            cur = conn.execute(
                "INSERT INTO ventas (estado) VALUES ('abierta')"
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def set_cliente(self, venta_id: int, cliente_id: int | None, nombre: str) -> None:
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE ventas SET cliente_id=?, nombre_cliente=? WHERE id=?",
                (cliente_id, nombre, venta_id),
            )
            conn.commit()
        finally:
            conn.close()

    def sync_items(self, venta_id: int, items: list[VentaItem]) -> None:
        """Reemplaza todos los items de la venta."""
        conn = get_connection()
        try:
            conn.execute("DELETE FROM venta_items WHERE venta_id = ?", (venta_id,))
            for item in items:
                conn.execute(
                    """INSERT INTO venta_items
                       (venta_id, producto_id, variante_id, nombre_producto,
                        precio_unitario, cantidad, subtotal)
                       VALUES (?,?,?,?,?,?,?)""",
                    (venta_id, item.producto_id, item.variante_id,
                     item.nombre_producto, item.precio_unitario,
                     item.cantidad, item.subtotal),
                )
            conn.commit()
        finally:
            conn.close()

    def descontar_stock_por_venta(self, venta_id: int) -> None:
        """Descuenta el stock de cada variante vendida al cerrar la venta."""
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT variante_id, cantidad FROM venta_items"
                " WHERE venta_id = ? AND variante_id IS NOT NULL",
                (venta_id,),
            ).fetchall()
            for row in rows:
                conn.execute(
                    "UPDATE producto_variantes SET stock = MAX(0, stock - ?) WHERE id = ?",
                    (row["cantidad"], row["variante_id"]),
                )
            conn.commit()
        finally:
            conn.close()

    def cerrar(self, venta_id: int) -> None:
        conn = get_connection()
        try:
            conn.execute(
                """UPDATE ventas SET estado='cerrada',
                   fecha_cierre=datetime('now','localtime')
                   WHERE id=?""",
                (venta_id,),
            )
            conn.commit()
        finally:
            conn.close()

    def delete(self, venta_id: int) -> None:
        conn = get_connection()
        try:
            conn.execute("DELETE FROM ventas WHERE id=?", (venta_id,))
            conn.commit()
        finally:
            conn.close()


class PagoRepository:

    def find_by_venta(self, venta_id: int) -> list[Pago]:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM pagos WHERE venta_id=? ORDER BY fecha, id",
                (venta_id,),
            ).fetchall()
            return [Pago.from_row(r) for r in rows]
        finally:
            conn.close()

    def find_by_mes(self, anio: int, mes: int) -> list[Pago]:
        conn = get_connection()
        try:
            prefix = f"{anio:04d}-{mes:02d}"
            rows = conn.execute(
                "SELECT * FROM pagos WHERE fecha LIKE ? ORDER BY fecha, id",
                (f"{prefix}%",),
            ).fetchall()
            return [Pago.from_row(r) for r in rows]
        finally:
            conn.close()

    def create(self, p: Pago) -> int:
        conn = get_connection()
        try:
            cur = conn.execute(
                "INSERT INTO pagos (venta_id, monto, tipo, fecha) VALUES (?,?,?,?)",
                (p.venta_id, p.monto, p.tipo, p.fecha),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def delete(self, pago_id: int) -> None:
        conn = get_connection()
        try:
            conn.execute("DELETE FROM pagos WHERE id=?", (pago_id,))
            conn.commit()
        finally:
            conn.close()


venta_repository = VentaRepository()
pago_repository   = PagoRepository()
