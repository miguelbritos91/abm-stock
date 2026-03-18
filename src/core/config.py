"""
Constantes globales de la aplicación: rutas de archivos y directorio base.
Es el único lugar donde se define dónde vive cada recurso.

Soporta dos modos de ejecución:
- Desarrollo: desde el código fuente (python main.py)
- Producción: binario compilado con PyInstaller (--onedir)

En producción (MSI instalado en Program Files) los datos del usuario
(base de datos e imágenes) se guardan en:
  %LOCALAPPDATA%\ABMStock\
para evitar errores de permisos de escritura en Program Files.
"""
import os
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    # PyInstaller --onedir: el .exe puede estar en Program Files (solo lectura).
    # Los datos del usuario van a %LOCALAPPDATA%\ABMStock\ (siempre escribible).
    _appdata = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or ""
    DATA_DIR = Path(_appdata) / "ABMStock" if _appdata else Path(sys.executable).parent
    # Los assets (iconos, etc.) siguen junto al ejecutable (solo lectura está bien).
    BASE_DIR = Path(sys.executable).parent
else:
    # Ejecución desde código fuente
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    DATA_DIR = BASE_DIR

DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH    = DATA_DIR / "stock.db"
IMAGES_DIR = DATA_DIR / "images"
ASSETS_DIR = BASE_DIR / "assets"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
