
# ABM Stock - Gestión de Inventario

## Descripción
Aplicación de escritorio para Windows que permite gestionar el inventario de productos mediante un sistema ABM (Alta, Baja, Modificación) con base de datos SQLite.

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

