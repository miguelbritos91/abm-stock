"""
Servicio de Cliente: orquesta la lógica de negocio.
La UI solo habla con esta capa.
"""
import math
from src.models.cliente import Cliente
from src.repositories.cliente_repository import cliente_repository


class ClienteService:

    # ── Consultas ─────────────────────────────────────────────────────────

    def listar_paginado(
        self,
        search: str = "",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Cliente], int]:
        offset = (page - 1) * page_size
        if search:
            items = cliente_repository.search(search, offset=offset, limit=page_size)
            total = cliente_repository.count_search(search)
        else:
            items = cliente_repository.find_all(offset=offset, limit=page_size)
            total = cliente_repository.count_all()
        return items, total

    def calcular_total_paginas(self, total: int, page_size: int) -> int:
        return max(1, math.ceil(total / page_size))

    def obtener_por_id(self, cliente_id: int) -> Cliente | None:
        return cliente_repository.find_by_id(cliente_id)

    # ── Mutaciones ────────────────────────────────────────────────────────

    def crear(self, data: dict) -> int:
        self._validar(data)
        c = Cliente(
            cuit_dni=data.get("cuit_dni", "").strip(),
            nombre=data["nombre"].strip(),
            telefono=data["telefono"].strip(),
            direccion=data.get("direccion", "").strip(),
            email=data.get("email", "").strip(),
            fecha_nacimiento=data.get("fecha_nacimiento", "").strip(),
            sexo=data.get("sexo", "").strip(),
        )
        return cliente_repository.create(c)

    def actualizar(self, cliente_id: int, data: dict) -> None:
        self._validar(data)
        c = Cliente(
            id=cliente_id,
            cuit_dni=data.get("cuit_dni", "").strip(),
            nombre=data["nombre"].strip(),
            telefono=data["telefono"].strip(),
            direccion=data.get("direccion", "").strip(),
            email=data.get("email", "").strip(),
            fecha_nacimiento=data.get("fecha_nacimiento", "").strip(),
            sexo=data.get("sexo", "").strip(),
        )
        cliente_repository.update(c)

    def eliminar(self, cliente_id: int) -> None:
        cliente_repository.delete(cliente_id)

    # ── Validación ────────────────────────────────────────────────────────

    def _validar(self, data: dict) -> None:
        if not data.get("nombre", "").strip():
            raise ValueError("El nombre es obligatorio.")
        if not data.get("telefono", "").strip():
            raise ValueError("El teléfono es obligatorio.")


cliente_service = ClienteService()
