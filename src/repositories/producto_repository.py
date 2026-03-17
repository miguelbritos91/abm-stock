"""
Repositorio de Producto: unico responsable de todo el SQL relacionado
con las tablas productos, producto_variantes y producto_imagenes.
No aplica reglas de negocio -- solo traduce entre objetos del dominio
y filas de la base de datos.
"""
from src.core.database import get_connection
from src.models.producto import Producto, ProductoVariante, ProductoImagen


class ProductoRepository:

    # -- Helpers internos -------------------------------------------------

    def _load_variantes(self, conn, producto_id: int) -> list:
        rows = conn.execute(
            "SELECT * FROM producto_variantes WHERE producto_id = ? ORDER BY talla, color",
            (producto_id,),
        ).fetchall()
        return [ProductoVariante.from_row(r) for r in rows]

    def _load_imagenes(self, conn, producto_id: int) -> list:
        rows = conn.execute(
            "SELECT * FROM producto_imagenes WHERE producto_id = ? ORDER BY orden",
            (producto_id,),
        ).fetchall()
        return [ProductoImagen.from_row(r) for r in rows]

    def _enrich(self, conn, productos: list) -> list:
        """Carga variantes e imagenes para una lista de productos en el mismo conn."""
        for p in productos:
            p.variantes = self._load_variantes(conn, p.id)
            p.imagenes  = self._load_imagenes(conn, p.id)
        return productos

    # -- Consultas --------------------------------------------------------

    def find_all(self, offset: int = 0, limit: int = 20) -> list:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM productos ORDER BY nombre LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            return self._enrich(conn, [Producto.from_row(r) for r in rows])
        finally:
            conn.close()

    def count_all(self) -> int:
        conn = get_connection()
        try:
            return conn.execute("SELECT COUNT(*) AS n FROM productos").fetchone()["n"]
        finally:
            conn.close()

    def find_by_id(self, product_id: int):
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM productos WHERE id = ?", (product_id,)
            ).fetchone()
            if not row:
                return None
            p = Producto.from_row(row)
            p.variantes = self._load_variantes(conn, p.id)
            p.imagenes  = self._load_imagenes(conn, p.id)
            return p
        finally:
            conn.close()

    def search(self, query: str, offset: int = 0, limit: int = 20) -> list:
        like = f"%{query}%"
        conn = get_connection()
        try:
            rows = conn.execute(
                """SELECT DISTINCT p.*
                   FROM productos p
                   LEFT JOIN producto_variantes v ON v.producto_id = p.id
                   WHERE p.codigo      LIKE ?
                      OR p.nombre      LIKE ?
                      OR p.descripcion LIKE ?
                      OR p.categoria   LIKE ?
                      OR v.talla       LIKE ?
                      OR v.color       LIKE ?
                   ORDER BY p.nombre
                   LIMIT ? OFFSET ?""",
                (like, like, like, like, like, like, limit, offset),
            ).fetchall()
            return self._enrich(conn, [Producto.from_row(r) for r in rows])
        finally:
            conn.close()

    def count_search(self, query: str) -> int:
        like = f"%{query}%"
        conn = get_connection()
        try:
            return conn.execute(
                """SELECT COUNT(DISTINCT p.id) AS n
                   FROM productos p
                   LEFT JOIN producto_variantes v ON v.producto_id = p.id
                   WHERE p.codigo      LIKE ?
                      OR p.nombre      LIKE ?
                      OR p.descripcion LIKE ?
                      OR p.categoria   LIKE ?
                      OR v.talla       LIKE ?
                      OR v.color       LIKE ?""",
                (like, like, like, like, like, like),
            ).fetchone()["n"]
        finally:
            conn.close()

    def filter(
        self,
        search: str = "",
        categorias=None,
        tallas=None,
        colores=None,
        orden: str = "nombre",
    ) -> list:
        conditions = []
        params = []

        if search:
            like = f"%{search}%"
            conditions.append(
                "(p.codigo LIKE ? OR p.nombre LIKE ? OR p.descripcion LIKE ?"
                " OR p.categoria LIKE ? OR v.talla LIKE ? OR v.color LIKE ?)"
            )
            params.extend([like, like, like, like, like, like])

        if categorias:
            ph = ",".join("?" * len(categorias))
            conditions.append(f"p.categoria IN ({ph})")
            params.extend(categorias)

        if tallas:
            ph = ",".join("?" * len(tallas))
            conditions.append(f"v.talla IN ({ph})")
            params.extend(tallas)

        if colores:
            ph = ",".join("?" * len(colores))
            conditions.append(f"v.color IN ({ph})")
            params.extend(colores)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        _ORDER = {
            "nombre":     "p.nombre ASC",
            "precio_asc": "p.precio_unitario ASC",
            "precio_desc":"p.precio_unitario DESC",
        }
        order_clause = _ORDER.get(orden, "p.nombre ASC")

        sql = f"""
            SELECT DISTINCT p.*
            FROM productos p
            LEFT JOIN producto_variantes v ON v.producto_id = p.id
            {where}
            ORDER BY {order_clause}
        """
        conn = get_connection()
        try:
            rows = conn.execute(sql, params).fetchall()
            return self._enrich(conn, [Producto.from_row(r) for r in rows])
        finally:
            conn.close()

    def get_distinct_values(self, field: str) -> list:
        """Valores unicos de categoria (productos) o talla/color (producto_variantes)."""
        conn = get_connection()
        try:
            if field == "categoria":
                rows = conn.execute(
                    "SELECT DISTINCT categoria FROM productos"
                    " WHERE categoria IS NOT NULL AND categoria != '' ORDER BY categoria"
                ).fetchall()
            elif field in ("talla", "color"):
                rows = conn.execute(
                    f"SELECT DISTINCT {field} FROM producto_variantes"
                    f" WHERE {field} IS NOT NULL AND {field} != '' ORDER BY {field}"
                ).fetchall()
            else:
                return []
            return [r[0] for r in rows]
        finally:
            conn.close()

    # -- Mutaciones -------------------------------------------------------

    def insert(self, p: Producto) -> int:
        """Inserta el producto con sus variantes e imagenes. Retorna el nuevo id."""
        conn = get_connection()
        try:
            cur = conn.execute(
                """INSERT INTO productos
                   (codigo, nombre, descripcion, precio_costo,
                    porcentaje_ganancia, precio_unitario, categoria)
                   VALUES (?,?,?,?,?,?,?)""",
                (p.codigo, p.nombre, p.descripcion, p.precio_costo,
                 p.porcentaje_ganancia, p.precio_unitario, p.categoria),
            )
            product_id = cur.lastrowid
            self._save_variantes(conn, product_id, p.variantes)
            self._save_imagenes(conn, product_id, p.imagenes)
            conn.commit()
            return product_id
        finally:
            conn.close()

    def update(self, p: Producto) -> None:
        conn = get_connection()
        try:
            conn.execute(
                """UPDATE productos SET
                   codigo=?, nombre=?, descripcion=?, precio_costo=?,
                   porcentaje_ganancia=?, precio_unitario=?, categoria=?
                   WHERE id=?""",
                (p.codigo, p.nombre, p.descripcion, p.precio_costo,
                 p.porcentaje_ganancia, p.precio_unitario, p.categoria,
                 p.id),
            )
            self._save_variantes(conn, p.id, p.variantes)
            self._save_imagenes(conn, p.id, p.imagenes)
            conn.commit()
        finally:
            conn.close()

    def delete(self, product_id: int) -> list:
        """
        Elimina el producto (CASCADE borra variantes e imagenes en BD).
        Retorna la lista de filenames de imagenes para borrar del disco.
        """
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT filename FROM producto_imagenes WHERE producto_id = ?",
                (product_id,),
            ).fetchall()
            filenames = [r["filename"] for r in rows]
            conn.execute("DELETE FROM productos WHERE id = ?", (product_id,))
            conn.commit()
            return filenames
        finally:
            conn.close()

    # -- Sincronizacion de variantes --------------------------------------

    def _save_variantes(self, conn, product_id: int, variantes: list):
        incoming_ids = {v.id for v in variantes if v.id is not None}
        existing = conn.execute(
            "SELECT id FROM producto_variantes WHERE producto_id = ?", (product_id,)
        ).fetchall()
        for row in existing:
            if row["id"] not in incoming_ids:
                conn.execute("DELETE FROM producto_variantes WHERE id = ?", (row["id"],))
        for v in variantes:
            if v.id is not None:
                conn.execute(
                    "UPDATE producto_variantes SET talla=?, color=?, stock=? WHERE id=?",
                    (v.talla, v.color, v.stock, v.id),
                )
            else:
                conn.execute(
                    """INSERT OR REPLACE INTO producto_variantes
                       (producto_id, talla, color, stock) VALUES (?,?,?,?)""",
                    (product_id, v.talla, v.color, v.stock),
                )

    def upsert_variante(self, product_id: int, variante: ProductoVariante) -> int:
        conn = get_connection()
        try:
            if variante.id is not None:
                conn.execute(
                    "UPDATE producto_variantes SET talla=?, color=?, stock=? WHERE id=?",
                    (variante.talla, variante.color, variante.stock, variante.id),
                )
                conn.commit()
                return variante.id
            cur = conn.execute(
                """INSERT OR REPLACE INTO producto_variantes
                   (producto_id, talla, color, stock) VALUES (?,?,?,?)""",
                (product_id, variante.talla, variante.color, variante.stock),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def delete_variante(self, variante_id: int) -> None:
        conn = get_connection()
        try:
            conn.execute("DELETE FROM producto_variantes WHERE id = ?", (variante_id,))
            conn.commit()
        finally:
            conn.close()

    # -- Sincronizacion de imagenes ----------------------------------------

    def _save_imagenes(self, conn, product_id: int, imagenes: list):
        existing_ids = {
            r["id"] for r in conn.execute(
                "SELECT id FROM producto_imagenes WHERE producto_id = ?", (product_id,)
            ).fetchall()
        }
        incoming_ids = {img.id for img in imagenes if img.id is not None}
        for eid in existing_ids - incoming_ids:
            conn.execute("DELETE FROM producto_imagenes WHERE id = ?", (eid,))
        for orden, img in enumerate(imagenes):
            if img.id is None:
                conn.execute(
                    "INSERT INTO producto_imagenes (producto_id, filename, orden) VALUES (?,?,?)",
                    (product_id, img.filename, orden),
                )
            else:
                conn.execute(
                    "UPDATE producto_imagenes SET orden=? WHERE id=?",
                    (orden, img.id),
                )

    def add_imagen(self, product_id: int, filename: str, orden: int = 0) -> int:
        conn = get_connection()
        try:
            cur = conn.execute(
                "INSERT INTO producto_imagenes (producto_id, filename, orden) VALUES (?,?,?)",
                (product_id, filename, orden),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def delete_imagen(self, imagen_id: int) -> str:
        """Elimina el registro y retorna el filename para borrar del disco."""
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT filename FROM producto_imagenes WHERE id = ?", (imagen_id,)
            ).fetchone()
            filename = row["filename"] if row else ""
            conn.execute("DELETE FROM producto_imagenes WHERE id = ?", (imagen_id,))
            conn.commit()
            return filename
        finally:
            conn.close()


# Instancia singleton -- toda la app importa este objeto directamente.
producto_repository = ProductoRepository()
