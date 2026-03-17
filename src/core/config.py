"""
Constantes globales de la aplicación: rutas de archivos y directorio base.
Es el único lugar donde se define dónde vive cada recurso.

Soporta dos modos de ejecución:
- Desarrollo: desde el código fuente (python main.py)
- Producción: binario compilado con PyInstaller (--onedir)
"""
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    # PyInstaller --onedir: el .exe vive en la carpeta de instalación.
    # stock.db e images/ deben estar junto al ejecutable.
    BASE_DIR = Path(sys.executable).parent
else:
    # Ejecución desde código fuente: subir tres niveles (src/core/config.py → /)
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

DB_PATH    = BASE_DIR / "stock.db"
IMAGES_DIR = BASE_DIR / "images"
ASSETS_DIR = BASE_DIR / "assets"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
