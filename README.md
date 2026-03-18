
# ABM Stock — Gestión de Inventario y Ventas

Aplicación de escritorio para Windows que centraliza la gestión de inventario, ventas, clientes y devoluciones en un único sistema sin dependencias externas ni conexión a internet.

---

## Características principales

| Módulo | Funcionalidad |
|--------|--------------|
| **Inicio** | Buscador global con filtros combinables, vista cuadrícula y tabla |
| **Productos** | ABM completo de productos con variantes (talla/color), stock e imágenes |
| **Ventas** | Registro de ventas con selección de variante, múltiples pagos y saldo pendiente |
| **Clientes** | Ficha de cliente con datos de contacto y fecha de nacimiento |
| **Historial** | Listado paginado de ventas con filtros y acceso al detalle |
| **Devoluciones** | Devolución parcial o total de ítems, con reintegro opcional al stock |

---

## Tecnología

- **Lenguaje**: Python 3.10+
- **GUI**: tkinter + ttk (incluido con Python)
- **Base de datos**: SQLite (incluido con Python)
- **Imágenes**: Pillow
- **Selector de fechas**: tkcalendar + babel
- **Empaquetado**: PyInstaller 6 + WiX MSI

---

## Instalación

### Opción A — Instalador MSI (recomendado)

1. Descargar `ABMStock_v1.0.0.msi` desde la carpeta `builds/`
2. Ejecutar el instalador como **Administrador**
3. Seguir el asistente (permite elegir carpeta de instalación)
4. El acceso directo queda en el Escritorio y en el Menú Inicio

> Los datos del usuario (base de datos e imágenes) se guardan en  
> `%LOCALAPPDATA%\ABMStock\` — nunca dentro de Program Files.

### Opción B — Ejecución desde código fuente

```bash
# 1. Clonar el repositorio
git clone <url>
cd abm-stock

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar
python main.py
```

En Windows también se puede hacer doble clic en `run.bat`.

### Requisitos del sistema

- Windows 10 / 11 (64-bit)
- Python 3.10 o superior (solo para ejecución desde fuente)
- Sin base de datos externa ni internet requeridos

---

## Uso de la aplicación

### Inicio — Exploración del catálogo

La pantalla principal muestra todos los productos disponibles.

- **Buscador**: filtra en tiempo real por código, nombre, talla, color, descripción y categoría.
- **Filtros desplegables** (combinables entre sí):
  - Categoría
  - Talla
  - Color
  - Orden por precio (menor → mayor / mayor → menor)
- **Vistas**:
  - **Cuadrícula**: cards tipo catálogo con imagen, nombre, talla, color y precio. Clic → detalle completo.
  - **Tabla**: listado compacto con todas las columnas. Doble clic → detalle completo.
- Desde el **modal de detalle** se puede agregar el producto directamente a una venta activa.

---

### Productos — Gestión de inventario

Listado paginado (15 ítems/página) con buscador integrado.

**Campos de un producto:**

| Campo | Descripción |
|-------|-------------|
| Código | Identificador único (ej. `CAM-001`) |
| Nombre | Nombre descriptivo |
| Descripción | Texto libre adicional |
| Categoría | Clasificación (ej. `Remeras`, `Pantalones`) |
| Precio de costo | Costo de adquisición |
| % Ganancia | Se aplica sobre el costo para calcular el precio unitario |
| Precio unitario | Calculado automáticamente (`costo × (1 + %ganancia/100)`) |
| Imagen | Foto del producto (se copia internamente) |

**Variantes (talla + color + stock):**  
Cada producto puede tener múltiples variantes. Por ejemplo: `Talle M / Blanco — stock: 5`. El stock se descuenta automáticamente al cerrar una venta.

**Acciones disponibles:**
- **Nuevo producto**: abre formulario con carga de imagen.
- **Editar**: modifica datos y variantes del producto seleccionado.
- **Eliminar**: borra el producto y todas sus variantes e imágenes asociadas.

---

### Ventas — Registro de ventas

Permite crear una venta seleccionando cliente, productos, cantidades y forma de pago.

**Flujo de una venta:**

1. Seleccionar o crear un cliente (o dejar en blanco).
2. Buscar productos y hacer clic en **Agregar a venta**.
3. Si el producto tiene variantes, aparece un selector de talla y color.
4. Ingresar la cantidad deseada.
5. Registrar uno o más pagos:
   - Efectivo / Transferencia / Tarjeta
   - Fecha del pago (selector de calendario)
   - Monto (botón **Pagar saldo** completa el monto faltante)
6. **Cerrar venta**: descuenta el stock de las variantes correspondientes.

Una venta puede quedar con **saldo pendiente** y completarse con pagos posteriores.

---

### Clientes — Ficha de cliente

ABM de clientes con los siguientes datos:

| Campo | Descripción |
|-------|-------------|
| Nombre | Nombre completo |
| Teléfono | Contacto principal |
| CUIT / DNI | Documento de identidad |
| Dirección | Domicilio |
| Email | Correo electrónico |
| Fecha de nacimiento | Selector de calendario |
| Sexo | M / F / Otro |

Desde la sección de ventas se puede crear un nuevo cliente al vuelo sin salir del formulario.

---

### Historial de ventas

Listado paginado de todas las ventas registradas.

- **Filtros**: rango de fechas, cliente, estado (pagada / con saldo).
- **Columnas**: fecha, cliente, total, total pagado, saldo, estado.
- **Detalle**: al seleccionar una venta se abre el modal de detalle con ítems, pagos y devoluciones.
- Desde el detalle se puede **registrar un pago adicional** o **devolver un ítem**.

---

### Devoluciones

Disponibles desde el modal de detalle de cualquier venta.

**Por cada ítem se puede devolver:**

| Campo | Descripción |
|-------|-------------|
| Cantidad a devolver | Parcial o total |
| ¿Vuelve al stock? | Si las unidades se reincorporan al inventario |
| Cantidad a reponer | De las devueltas, cuántas se reponen |
| Observación | Motivo u observación libre |
| Fecha | Fecha de la devolución |

El **saldo de la venta** se recalcula automáticamente descontando el monto devuelto:

```
Total ajustado = Total venta − Total devoluciones
Saldo          = Total ajustado − Total pagado
```

Un ítem puede aparecer como **Devuelto** (total) o **Parcial** en la tabla de ítems.

---

## Estructura del proyecto

```
abm-stock/
├── main.py                          # Punto de entrada
├── run.bat                          # Ejecutar en desarrollo (Windows)
├── build.bat                        # Compilar MSI para distribución
├── requirements.txt                 # Dependencias: pillow, tkcalendar, babel
├── hooks/
│   └── hook-tkcalendar.py           # Hook PyInstaller para tkcalendar
├── scripts/
│   └── build_installer.py           # Genera MSI (WiX), EXE (Inno) o ZIP
├── assets/
│   └── icon.ico                     # Ícono de la aplicación
└── src/
    ├── core/
    │   ├── app_info.py              # APP_NAME, VERSION
    │   ├── config.py                # Rutas: BASE_DIR, DATA_DIR, DB_PATH, IMAGES_DIR
    │   └── database.py              # Conexión SQLite, esquema y migraciones
    │
    ├── models/                      # Datos puros (dataclasses, sin SQL ni UI)
    │   ├── producto.py              # Producto, ProductoVariante, ProductoImagen
    │   ├── cliente.py               # Cliente
    │   ├── venta.py                 # Venta, VentaItem, Pago
    │   └── devolucion.py            # Devolucion
    │
    ├── repositories/                # Acceso a datos (SQL puro)
    │   ├── producto_repository.py
    │   ├── cliente_repository.py
    │   ├── venta_repository.py
    │   └── devolucion_repository.py
    │
    ├── services/                    # Lógica de negocio
    │   ├── imagen_service.py        # Copia/elimina imágenes de productos
    │   ├── producto_service.py      # Cálculo de precios, orquesta imágenes
    │   ├── cliente_service.py
    │   ├── venta_service.py         # Cierre de venta, descuento de stock
    │   └── devolucion_service.py    # Registra devolución y reintegra stock
    │
    └── ui/                          # Capa de presentación (tkinter)
        ├── styles.py                # Paleta de colores, fuentes, fmt_moneda()
        ├── widgets.py               # DropdownCheckbox, Pagination, etc.
        ├── app.py                   # Ventana principal + sidebar de navegación
        ├── home_section.py          # Inicio: buscador, filtros, cuadrícula/tabla
        ├── products_section.py      # Productos: listado paginado, ABM
        ├── product_form_modal.py    # Formulario nuevo/editar producto
        ├── product_detail_modal.py  # Detalle de producto, botón agregar a venta
        ├── venta_section.py         # Nueva venta: carrito, pagos, cierre
        ├── venta_detail_modal.py    # Detalle de venta: ítems, pagos, devoluciones
        ├── clientes_section.py      # Listado y ABM de clientes
        ├── cliente_form_modal.py    # Formulario nuevo/editar cliente
        ├── historial_ventas_section.py  # Historial paginado con filtros
        └── about_modal.py           # Modal "Acerca de"
```

### Arquitectura en capas

```
UI  →  Services  →  Repositories  →  Database
UI  →  Models   ←   Services     ←   Repositories
```

- La **UI** nunca ejecuta SQL directamente.
- Los **repositorios** no aplican lógica de negocio.
- Los **servicios** orquestan repositorios y coordinan side-effects (stock, imágenes).
- Los **modelos** son dataclasses puras, reutilizables en cualquier capa.

---

## Base de datos

SQLite ubicada en `%LOCALAPPDATA%\ABMStock\stock.db` (instalado) o `stock.db` en la raíz del proyecto (desarrollo).

### Tablas

| Tabla | Descripción |
|-------|-------------|
| `productos` | Catálogo principal de productos |
| `producto_variantes` | Combinaciones talla + color + stock por producto |
| `producto_imagenes` | Rutas de imágenes asociadas a un producto |
| `clientes` | Ficha de clientes |
| `ventas` | Cabecera de cada venta (cliente, fecha, estado) |
| `venta_items` | Líneas de producto dentro de cada venta |
| `pagos` | Pagos registrados contra una venta |
| `devoluciones` | Devoluciones de ítems con reintegro opcional de stock |

---

## Build — Generar instalador

```bash
build.bat
```

El script realiza automáticamente:

1. Verifica Python instalado
2. Instala `pyinstaller` y `pillow`
3. Limpia compilaciones anteriores
4. Compila el ejecutable con PyInstaller (incluye DLLs de Python y VC++)
5. Genera el instalador en el orden de prioridad:
   - **MSI** (WiX 4 o WiX 3 — se descarga automáticamente si no está instalado)
   - **EXE** (Inno Setup, si está instalado)
   - **ZIP portable** (fallback siempre disponible)

Los artefactos finales quedan en la carpeta `builds/`.

---

## Licencia

Software libre para uso interno de gestión de inventario.


## Características

### Datos del Producto
- Código único
- Nombre y descripción
- Categoría
- Talla y color
- Stock disponible
- Precio de costo y precio unitario (con margen de ganancia)
- Imagen

### Secciones de la App

#### 1. Inicio - Búsqueda y Exploración
- **Buscador**: Busca por código, nombre, color, talla, descripción, categoría
- **Filtros combinables** (desplegables con checkbox):
    - Categoría
    - Talla
    - Color
    - Ordenamiento: Menor a mayor / Mayor a menor precio
- **Vistas disponibles**:
    - Tabla: Listado con encabezados y detalles completos
    - Cuadrícula: Cards tipo Mercado Libre con imagen, nombre, color, talla y precio
    - Modal de detalle: Al hacer clic en card muestra todos los datos

#### 2. Productos - Gestión Completa
- **Listado paginado** de todos los productos
- **Buscador**: Filtra por código, nombre, talla, color, descripción, categoría
- **Botones por producto**: Editar y eliminar
- **Botón "Nuevo Producto"**: Abre modal con formulario
    - Incluye carga de imágenes
    - Las imágenes se guardan en carpeta `/images` dentro del directorio de instalación

## Tecnología
- **Backend**: Python 3.10+
- **GUI**: tkinter (incluido con Python)
- **Base de datos**: SQLite (incluido con Python)
- **Procesamiento de imágenes**: Pillow
- **Almacenamiento de imágenes**: Carpeta local `/images`

## Estructura del proyecto

Arquitectura en capas **Repository + Service** para separar responsabilidades:

```
abm-stock/
├── main.py                            # Punto de entrada
├── run.bat                            # Ejecutar en Windows (instala deps + lanza app)
├── requirements.txt                   # pillow
├── stock.db                           # Base de datos SQLite (se crea automáticamente)
├── images/                            # Imágenes de productos (copiadas al guardar)
├── assets/                            # Recursos extra (icon.ico, etc.)
└── src/
    ├── core/                          # Infraestructura base
    │   ├── config.py                  # Rutas globales: BASE_DIR, DB_PATH, IMAGES_DIR
    │   └── database.py                # Conexión SQLite y creación del esquema
    │
    ├── models/                        # Modelos de dominio (datos puros, sin SQL ni UI)
    │   └── producto.py                # dataclass Producto + from_row/from_dict/to_dict
    │
    ├── repositories/                  # Acceso a datos (mini-ORM manual)
    │   └── producto_repository.py     # Todo el SQL: find_all, filter, insert, update, delete
    │
    ├── services/                      # Lógica de negocio
    │   ├── imagen_service.py          # Guardar/eliminar/resolver ruta de imágenes
    │   └── producto_service.py        # Orquesta repositorio + imágenes, calcula precios
    │
    └── ui/                            # Capa de presentación (tkinter)
        ├── styles.py                  # Paleta de colores y estilos
        ├── widgets.py                 # Widgets reutilizables (DropdownCheckbox, Pagination)
        ├── app.py                     # Ventana principal + sidebar de navegación
        ├── home_section.py            # Sección Inicio (buscador, filtros, cuadrícula/tabla)
        ├── products_section.py        # Sección Productos (listado paginado, ABM)
        ├── product_form_modal.py      # Modal formulario nuevo/editar producto
        └── product_detail_modal.py    # Modal detalle de producto
```

### Flujo de dependencias
```
ui  →  services  →  repositories  →  core/database
ui  →  models  ←   services      ←   repositories
```
La UI nunca toca SQL directamente. Los repositorios nunca aplican lógica de negocio.

## Instalación y ejecución

### Requisitos
- Python 3.10 o superior instalado en el sistema
- pip disponible

### Pasos
1. Clonar o descargar el proyecto
2. Abrir una terminal en la carpeta del proyecto
3. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
4. Ejecutar la aplicación:
   ```bash
   python main.py
   ```

### Atajo en Windows
Hacer doble clic en `run.bat` — instala dependencias y abre la app automáticamente.

## Uso

### Sección Inicio
- Escribir en el buscador para filtrar productos por código, nombre, color, talla, descripción o categoría
- Usar los botones desplegables de **Categoría**, **Talla**, **Color** y **Ordenar precio** para combinar filtros
- Alternar entre vista **Cuadrícula** (cards con imagen) y **Tabla** (listado detallado)
- En vista cuadrícula: hacer clic en una card para ver el detalle completo
- En vista tabla: doble clic en una fila para ver el detalle completo

### Sección Productos
- Listado paginado (15 productos por página) con buscador integrado
- Botón **+ Nuevo Producto** para agregar un producto con imagen
- Seleccionar una fila y usar los botones **Editar** / **Eliminar**
- El precio unitario se calcula automáticamente al ingresar costo y % de ganancia

