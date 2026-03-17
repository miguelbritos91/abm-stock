"""
Servicio de Venta: orquesta lógica de negocio sobre ventas y pagos.
"""
import math
from datetime import date

from src.models.venta import Venta, VentaItem, Pago
from src.repositories.venta_repository import venta_repository, pago_repository


class VentaService:

    # ── Venta activa ─────────────────────────────────────────────────────

    def obtener_o_crear_abierta(self) -> Venta:
        """Retorna la venta abierta existente, o crea una nueva."""
        venta = venta_repository.find_abierta()
        if venta is None:
            vid = venta_repository.create()
            venta = venta_repository.find_by_id(vid)
        return venta

    def obtener_por_id(self, venta_id: int) -> Venta | None:
        return venta_repository.find_by_id(venta_id)

    def set_cliente(self, venta_id: int, cliente_id: int | None, nombre: str) -> None:
        venta_repository.set_cliente(venta_id, cliente_id, nombre)

    def sync_items(self, venta_id: int, items: list[VentaItem]) -> None:
        venta_repository.sync_items(venta_id, items)

    def cerrar(self, venta_id: int) -> None:
        venta = venta_repository.find_by_id(venta_id)
        if not venta:
            raise ValueError("Venta no encontrada.")
        if not venta.items:
            raise ValueError("No se puede cerrar una venta sin productos.")
        if not venta.cliente_id:
            raise ValueError("Debe asignar un cliente antes de cerrar la venta.")
        venta_repository.cerrar(venta_id)
        venta_repository.descontar_stock_por_venta(venta_id)

    def cancelar(self, venta_id: int) -> None:
        """Elimina la venta abierta (descarta el carrito)."""
        venta_repository.delete(venta_id)

    # ── Historial ─────────────────────────────────────────────────────────

    def listar_historial(
        self,
        search: str = "",
        fecha_desde: str = "",
        fecha_hasta: str = "",
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[Venta], int]:
        offset = (page - 1) * page_size
        items  = venta_repository.find_historial(
            search=search, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
            offset=offset, limit=page_size,
        )
        total = venta_repository.count_historial(
            search=search, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
        )
        return items, total

    def calcular_total_paginas(self, total: int, page_size: int) -> int:
        return max(1, math.ceil(total / page_size))

    # ── Pagos ─────────────────────────────────────────────────────────────

    def agregar_pago(self, venta_id: int, monto: float, tipo: str, fecha: str = "") -> Pago:
        if monto <= 0:
            raise ValueError("El monto del pago debe ser mayor a cero.")
        if tipo not in ("efectivo", "transferencia", "tarjeta"):
            raise ValueError("Tipo de pago inválido.")
        fecha = fecha or str(date.today())
        p = Pago(venta_id=venta_id, monto=monto, tipo=tipo, fecha=fecha)
        p.id = pago_repository.create(p)
        return p

    def eliminar_pago(self, pago_id: int) -> None:
        pago_repository.delete(pago_id)

    def pagos_por_mes(self, anio: int, mes: int) -> list[Pago]:
        return pago_repository.find_by_mes(anio, mes)


venta_service = VentaService()
