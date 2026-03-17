
# ABM Stock - Gestión de Inventario

## Descripción
Aplicación de escritorio para Windows que permite gestionar el inventario de prendas femeninas mediante un sistema ABM (Alta, Baja, Modificación) con base de datos SQLite.

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
- **Backend**: Python
- **Base de datos**: SQLite
- **Almacenamiento de imágenes**: Carpeta local `/images`
