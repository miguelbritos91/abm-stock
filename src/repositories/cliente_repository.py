"""
Repositorio de Cliente: único responsable del SQL sobre la tabla clientes.
No aplica reglas de negocio.
"""
from src.core.database import get_connection
from src.models.cliente import Cliente


class ClienteRepository:

    # ── Consultas ─────────────────────────────────────────────────────────

    def find_all(self, offset: int = 0, limit: int = 50) -> list[Cliente]:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM clientes ORDER BY nombre LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            return [Cliente.from_row(r) for r in rows]
        finally:
            conn.close()

    def count_all(self) -> int:
        conn = get_connection()
        try:
            return conn.execute("SELECT COUNT(*) AS n FROM clientes").fetchone()["n"]
        finally:
            conn.close()

    def find_by_id(self, cliente_id: int) -> Cliente | None:
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM clientes WHERE id = ?", (cliente_id,)
            ).fetchone()
            return Cliente.from_row(row) if row else None
        finally:
            conn.close()

    def search(self, query: str, offset: int = 0, limit: int = 50) -> list[Cliente]:
        like = f"%{query}%"
        conn = get_connection()
        try:
            rows = conn.execute(
                """SELECT * FROM clientes
                   WHERE nombre   LIKE ?
                      OR telefono LIKE ?
                      OR cuit_dni LIKE ?
                      OR email    LIKE ?
                   ORDER BY nombre LIMIT ? OFFSET ?""",
                (like, like, like, like, limit, offset),
            ).fetchall()
            return [Cliente.from_row(r) for r in rows]
        finally:
            conn.close()

    def count_search(self, query: str) -> int:
        like = f"%{query}%"
        conn = get_connection()
        try:
            return conn.execute(
                """SELECT COUNT(*) AS n FROM clientes
                   WHERE nombre   LIKE ?
                      OR telefono LIKE ?
                      OR cuit_dni LIKE ?
                      OR email    LIKE ?""",
                (like, like, like, like),
            ).fetchone()["n"]
        finally:
            conn.close()

    # ── Mutaciones ────────────────────────────────────────────────────────

    def create(self, c: Cliente) -> int:
        conn = get_connection()
        try:
            cur = conn.execute(
                """INSERT INTO clientes
                   (cuit_dni, nombre, telefono, direccion, email, fecha_nacimiento, sexo)
                   VALUES (?,?,?,?,?,?,?)""",
                (c.cuit_dni, c.nombre, c.telefono, c.direccion,
                 c.email, c.fecha_nacimiento, c.sexo),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def update(self, c: Cliente) -> None:
        conn = get_connection()
        try:
            conn.execute(
                """UPDATE clientes SET
                   cuit_dni=?, nombre=?, telefono=?, direccion=?,
                   email=?, fecha_nacimiento=?, sexo=?
                   WHERE id=?""",
                (c.cuit_dni, c.nombre, c.telefono, c.direccion,
                 c.email, c.fecha_nacimiento, c.sexo, c.id),
            )
            conn.commit()
        finally:
            conn.close()

    def delete(self, cliente_id: int) -> None:
        conn = get_connection()
        try:
            conn.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
            conn.commit()
        finally:
            conn.close()


cliente_repository = ClienteRepository()
