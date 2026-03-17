"""
Servicio de imágenes: responsable de copiar, eliminar y resolver rutas
de las imágenes dentro del directorio /images de la aplicación.
No sabe nada de SQL ni de tkinter.
"""
import shutil
import uuid
from pathlib import Path

from src.core.config import IMAGES_DIR


class ImagenService:

    def save(self, src_path: str) -> str:
        """
        Copia la imagen origen al directorio /images usando un nombre UUID
        para evitar colisiones entre archivos.
        Retorna el nombre del archivo guardado, o '' si el origen no existe.
        """
        src = Path(src_path)
        if not src.exists():
            return ""

        dest_name = uuid.uuid4().hex + src.suffix.lower()
        shutil.copy2(str(src), str(IMAGES_DIR / dest_name))
        return dest_name

    def delete(self, filename: str) -> None:
        """Elimina el archivo del directorio /images si existe."""
        if filename:
            path = IMAGES_DIR / filename
            if path.exists():
                path.unlink()

    def get_path(self, filename: str) -> str:
        """Retorna la ruta absoluta de una imagen dado su nombre de archivo."""
        if not filename:
            return ""
        return str(IMAGES_DIR / filename)


# Instancia singleton para uso en toda la app.
imagen_service = ImagenService()
