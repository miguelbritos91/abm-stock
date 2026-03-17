"""
Servicio de Devoluciones: orquesta la lógica de negocio de retornos de items.
"""
from datetime import date

from src.models.devolucion import Devolucion
from src.models.venta import VentaItem
from src.repositories.devolucion_repository import devolucion_repository


class DevolucionService:

    def registrar(
        self,
        item: VentaItem,
        cantidad_devuelta: int,
        cantidad_a_stock: int,
        observacion: str = "",
        fecha: str = "",
    ) -> Devolucion:
        """
        Registra la devolución de `cantidad_devuelta` unidades de un ítem.
        Si `cantidad_a_stock` > 0 y el ítem tiene variante_id, repone stock.
        Retorna el objeto Devolucion creado.
        """
        if item.id is None:
            raise ValueError("El ítem no tiene id — no fue persistido.")
        if item.devolucion is not None:
            raise ValueError("Este ítem ya tiene una devolución registrada.")
        if cantidad_devuelta < 1 or cantidad_devuelta > item.cantidad:
            raise ValueError(
                f"La cantidad devuelta ({cantidad_devuelta}) debe estar entre 1 y {item.cantidad}."
            )
        if cantidad_a_stock < 0 or cantidad_a_stock > cantidad_devuelta:
            raise ValueError(
                f"La cantidad a reponer ({cantidad_a_stock}) no puede superar "
                f"la cantidad devuelta ({cantidad_devuelta})."
            )

        monto = round(item.precio_unitario * cantidad_devuelta, 2)
        dev = Devolucion(
            venta_item_id=item.id,
            venta_id=item.venta_id,
            cantidad_devuelta=cantidad_devuelta,
            cantidad_a_stock=cantidad_a_stock,
            monto_devuelto=monto,
            fecha=fecha or date.today().isoformat(),
            observacion=observacion,
        )
        dev.id = devolucion_repository.create(dev)

        if cantidad_a_stock > 0 and item.variante_id:
            devolucion_repository.reintegrar_stock(item.variante_id, cantidad_a_stock)

        return dev


devolucion_service = DevolucionService()
