"""
Gestión de la conexión SQLite y definición del esquema (migraciones).
No contiene lógica de negocio ni acceso a modelos.
"""
import sqlite3
from src.core.config import DB_PATH, IMAGES_DIR


def get_connection() -> sqlite3.Connection:
    """Abre y retorna una conexión con row_factory configurado."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """
    Inicializa la base de datos: crea el directorio de imágenes y
    aplica el esquema. Migra automáticamente datos del modelo anterior
    si existen (talla/color/stock/imagen en productos).
    """
    IMAGES_DIR.mkdir(exist_ok=True)
    conn = get_connection()
    try:
        # ── Tabla principal de productos ──────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo              TEXT    NOT NULL UNIQUE,
                nombre              TEXT    NOT NULL,
                descripcion         TEXT    DEFAULT '',
                precio_costo        REAL    DEFAULT 0,
                porcentaje_ganancia REAL    DEFAULT 0,
                precio_unitario     REAL    DEFAULT 0,
                categoria           TEXT    DEFAULT ''
            )
        """)

        # ── Variantes: cada combinación talla+color con su stock ──────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS producto_variantes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                producto_id INTEGER NOT NULL,
                talla       TEXT    NOT NULL DEFAULT '',
                color       TEXT    NOT NULL DEFAULT '',
                stock       INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE,
                UNIQUE (producto_id, talla, color)
            )
        """)

        # ── Imágenes: múltiples por producto, almacenadas por UUID ────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS producto_imagenes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                producto_id INTEGER NOT NULL,
                filename    TEXT    NOT NULL,
                orden       INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
            )
        """)

        # ── Tabla de clientes ─────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                cuit_dni         TEXT    DEFAULT '',
                nombre           TEXT    NOT NULL,
                telefono         TEXT    NOT NULL,
                direccion        TEXT    DEFAULT '',
                email            TEXT    DEFAULT '',
                fecha_nacimiento TEXT    DEFAULT '',
                sexo             TEXT    DEFAULT ''
            )
        """)

        # ── Ventas ────────────────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ventas (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id      INTEGER REFERENCES clientes(id) ON DELETE SET NULL,
                nombre_cliente  TEXT    DEFAULT '',
                estado          TEXT    NOT NULL DEFAULT 'abierta',
                fecha_apertura  TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
                fecha_cierre    TEXT    DEFAULT ''
            )
        """)

        # ── Items de venta ────────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS venta_items (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                venta_id         INTEGER NOT NULL REFERENCES ventas(id) ON DELETE CASCADE,
                producto_id      INTEGER REFERENCES productos(id) ON DELETE SET NULL,
                variante_id      INTEGER REFERENCES producto_variantes(id) ON DELETE SET NULL,
                nombre_producto  TEXT    NOT NULL DEFAULT '',
                precio_unitario  REAL    NOT NULL DEFAULT 0,
                cantidad         INTEGER NOT NULL DEFAULT 1,
                subtotal         REAL    NOT NULL DEFAULT 0
            )
        """)

        # ── Pagos ─────────────────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pagos (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                venta_id INTEGER NOT NULL REFERENCES ventas(id) ON DELETE CASCADE,
                monto    REAL    NOT NULL DEFAULT 0,
                tipo     TEXT    NOT NULL DEFAULT 'efectivo',
                fecha    TEXT    NOT NULL DEFAULT (date('now','localtime'))
            )
        """)

        # ── Devoluciones ──────────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS devoluciones (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                venta_item_id     INTEGER NOT NULL REFERENCES venta_items(id) ON DELETE CASCADE,
                venta_id          INTEGER NOT NULL REFERENCES ventas(id) ON DELETE CASCADE,
                cantidad_devuelta INTEGER NOT NULL DEFAULT 1,
                cantidad_a_stock  INTEGER NOT NULL DEFAULT 0,
                monto_devuelto    REAL    NOT NULL DEFAULT 0,
                fecha             TEXT    NOT NULL DEFAULT (date('now','localtime')),
                observacion       TEXT    DEFAULT ''
            )
        """)

        conn.commit()

        # ── Migración desde el esquema anterior ───────────────────────────
        _migrate_legacy(conn)

    finally:
        conn.close()


def _migrate_legacy(conn: sqlite3.Connection) -> None:
    """
    Si la tabla productos todavía tiene las columnas del modelo anterior
    (talla, color, stock, imagen), migra esos datos a las nuevas tablas
    y luego elimina las columnas legacy.
    SQLite no soporta DROP COLUMN antes de la versión 3.35; usamos
    recreación de tabla para compatibilidad amplia.
    """
    # Migración: agregar variante_id a venta_items si no existe
    vi_cols = {row[1] for row in conn.execute("PRAGMA table_info(venta_items)")}
    if "variante_id" not in vi_cols:
        conn.execute(
            "ALTER TABLE venta_items ADD COLUMN variante_id INTEGER"
            " REFERENCES producto_variantes(id) ON DELETE SET NULL"
        )
        conn.commit()

    # Migración: crear tabla devoluciones si no existe (DBs antiguas)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS devoluciones (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            venta_item_id     INTEGER NOT NULL REFERENCES venta_items(id) ON DELETE CASCADE,
            venta_id          INTEGER NOT NULL REFERENCES ventas(id) ON DELETE CASCADE,
            cantidad_devuelta INTEGER NOT NULL DEFAULT 1,
            cantidad_a_stock  INTEGER NOT NULL DEFAULT 0,
            monto_devuelto    REAL    NOT NULL DEFAULT 0,
            fecha             TEXT    NOT NULL DEFAULT (date('now','localtime')),
            observacion       TEXT    DEFAULT ''
        )
    """)
    conn.commit()

    cols = {row[1] for row in conn.execute("PRAGMA table_info(productos)")}
    if not (cols & {"talla", "color", "stock", "imagen"}):
        return  # ya migrado

    # Migrar variantes: una fila por producto legacy que tenga talla/color
    rows = conn.execute(
        "SELECT id, talla, color, stock FROM productos"
    ).fetchall()
    for row in rows:
        talla = (row["talla"] or "").strip()
        color = (row["color"] or "").strip()
        stock = int(row["stock"] or 0)
        if talla or color or stock:
            conn.execute(
                """INSERT OR IGNORE INTO producto_variantes
                   (producto_id, talla, color, stock) VALUES (?,?,?,?)""",
                (row["id"], talla, color, stock),
            )

    # Migrar imágenes legacy
    rows = conn.execute("SELECT id, imagen FROM productos").fetchall()
    for row in rows:
        filename = (row["imagen"] or "").strip()
        if filename:
            conn.execute(
                """INSERT OR IGNORE INTO producto_imagenes
                   (producto_id, filename, orden) VALUES (?,?,0)""",
                (row["id"], filename),
            )

    # Recrear tabla productos sin las columnas legacy
    conn.execute("""
        CREATE TABLE productos_new (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo              TEXT    NOT NULL UNIQUE,
            nombre              TEXT    NOT NULL,
            descripcion         TEXT    DEFAULT '',
            precio_costo        REAL    DEFAULT 0,
            porcentaje_ganancia REAL    DEFAULT 0,
            precio_unitario     REAL    DEFAULT 0,
            categoria           TEXT    DEFAULT ''
        )
    """)
    conn.execute("""
        INSERT INTO productos_new
            (id, codigo, nombre, descripcion,
             precio_costo, porcentaje_ganancia, precio_unitario, categoria)
        SELECT id, codigo, nombre, descripcion,
               precio_costo, porcentaje_ganancia, precio_unitario, categoria
        FROM productos
    """)
    conn.execute("DROP TABLE productos")
    conn.execute("ALTER TABLE productos_new RENAME TO productos")
    conn.commit()
