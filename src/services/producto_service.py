"""
Servicio de Producto: orquesta la lÃ³gica de negocio.

Coordina repositorio + servicio de imÃ¡genes y aplica las reglas del dominio
(cÃ¡lculo de precio, integridad de datos). La UI solo habla con esta capa.
"""
import math
from src.models.producto import Producto, ProductoVariante, ProductoImagen
from src.repositories.producto_repository import producto_repository
from src.services.imagen_service import imagen_service


class ProductoService:

    # â”€â”€ Consultas â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def listar_paginado(
        self,
        search: str = "",
        page: int = 1,
        page_size: int = 15,
    ) -> tuple[list[Producto], int]:
        """
        Retorna (lista_de_productos, total_de_resultados) para la pÃ¡gina indicada.
        Si hay texto de bÃºsqueda filtra por Ã©l; si no, trae todos.
        """
        offset = (page - 1) * page_size
        if search:
            items = producto_repository.search(search, offset=offset, limit=page_size)
            total = producto_repository.count_search(search)
        else:
            items = producto_repository.find_all(offset=offset, limit=page_size)
            total = producto_repository.count_all()
        return items, total

    def calcular_total_paginas(self, total: int, page_size: int) -> int:
        return max(1, math.ceil(total / page_size))

    def filtrar(
        self,
        search: str = "",
        categorias: list | None = None,
        tallas: list | None = None,
        colores: list | None = None,
        orden: str = "nombre",
    ) -> list[Producto]:
        """BÃºsqueda + filtros combinables para la secciÃ³n Inicio."""
        return producto_repository.filter(
            search=search,
            categorias=categorias,
            tallas=tallas,
            colores=colores,
            orden=orden,
        )

    def obtener_por_id(self, product_id: int) -> Producto | None:
        return producto_repository.find_by_id(product_id)

    def obtener_opciones_filtro(self) -> dict[str, list[str]]:
        """Retorna los valores distintos de categorÃ­a, talla y color para los dropdowns."""
        return {
            "categorias": producto_repository.get_distinct_values("categoria"),
            "tallas":     producto_repository.get_distinct_values("talla"),
            "colores":    producto_repository.get_distinct_values("color"),
        }

    def get_image_path(self, filename: str) -> str:
        return imagen_service.get_path(filename)

    # â”€â”€ Mutaciones â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def crear(
        self,
        data: dict,
        variantes: list[dict] | None = None,
        imagenes_src: list[str] | None = None,
    ) -> None:
        """
        Crea un nuevo producto.
        - `variantes`: lista de dicts con keys talla, color, stock.
        - `imagenes_src`: rutas locales de imÃ¡genes a guardar con UUID.
        - Recalcula precio_unitario desde costo + porcentaje.
        """
        variantes = variantes or []
        imagenes_src = imagenes_src or []

        imagenes = [
            ProductoImagen(filename=imagen_service.save(src), orden=i)
            for i, src in enumerate(imagenes_src)
            if src
        ]
        variantes_obj = [
            ProductoVariante(talla=v["talla"], color=v["color"], stock=int(v.get("stock", 0)))
            for v in variantes
        ]

        p = Producto.from_dict(data)
        p.precio_unitario = p.calcular_precio_unitario()
        p.variantes = variantes_obj
        p.imagenes  = imagenes
        producto_repository.insert(p)

    def actualizar(
        self,
        product_id: int,
        data: dict,
        variantes: list[dict] | None = None,
        imagenes_src: list[str] | None = None,
        imagenes_existentes: list[ProductoImagen] | None = None,
    ) -> None:
        """
        Actualiza un producto existente.
        - `variantes`: lista completa de variantes (reemplaza las anteriores).
        - `imagenes_src`: nuevas rutas a guardar (se agregan).
        - `imagenes_existentes`: objetos ProductoImagen que se conservan (con id).
        """
        variantes = variantes or []
        imagenes_src = imagenes_src or []
        imagenes_existentes = imagenes_existentes or []

        # Borrar del disco las imágenes que el usuario quitó
        producto_actual = producto_repository.find_by_id(product_id)
        if producto_actual:
            ids_conservados = {img.id for img in imagenes_existentes if img.id is not None}
            for img in producto_actual.imagenes:
                if img.id not in ids_conservados:
                    imagen_service.delete(img.filename)

        nuevas_imagenes = [
            ProductoImagen(filename=imagen_service.save(src), orden=len(imagenes_existentes) + i)
            for i, src in enumerate(imagenes_src)
            if src
        ]
        variantes_obj = [
            ProductoVariante(
                id=v.get("id"),
                producto_id=product_id,
                talla=v["talla"],
                color=v["color"],
                stock=int(v.get("stock", 0)),
            )
            for v in variantes
        ]

        p = Producto.from_dict({**data, "id": product_id})
        p.precio_unitario = p.calcular_precio_unitario()
        p.variantes = variantes_obj
        p.imagenes  = imagenes_existentes + nuevas_imagenes
        producto_repository.update(p)

    def eliminar(self, product_id: int) -> None:
        """Elimina el producto y borra todas sus imÃ¡genes del disco."""
        filenames = producto_repository.delete(product_id)
        for fn in filenames:
            imagen_service.delete(fn)


# Instancia singleton para uso en toda la app.
producto_service = ProductoService()
