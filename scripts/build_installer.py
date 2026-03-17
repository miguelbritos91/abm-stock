#!/usr/bin/env python3
"""
Genera el script Inno Setup (.iss) y compila el instalador ABM Stock.
Si Inno Setup no está instalado, genera además un ZIP portable como fallback.

Invocado por build.bat en el paso 5/5.
"""
import os
import sys
import subprocess
import zipfile
from pathlib import Path

# Inyectar la raiz del proyecto en el path para importar app_info
_PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(_PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(_PROJECT_DIR))

from src.core.app_info import APP_NAME, VERSION  # noqa: E402

try:
    import winreg
    HAS_WINREG = True
except ImportError:
    HAS_WINREG = False

# ── Rutas del proyecto ────────────────────────────────────────────────────────

PROJECT_DIR = _PROJECT_DIR
DIST_DIR    = PROJECT_DIR / "dist" / "ABMStock"
BUILDS_DIR  = PROJECT_DIR / "builds"
ICON_PATH   = PROJECT_DIR / "assets" / "icon.ico"

APP_VERSION = VERSION
EXE_NAME    = "ABMStock.exe"

# ── Plantilla ISS ─────────────────────────────────────────────────────────────
# Usa %(key)s para variables Python.
# {sd}, {app}, {group}, {#Define}, etc. son constantes de Inno Setup (sin escapar).

ISS_TEMPLATE = """\
; ============================================================
; Instalador generado automáticamente por build_installer.py
; ABM Stock v%(app_version)s  —  No editar manualmente.
; ============================================================

#define AppName      "%(app_name)s"
#define AppVersion   "%(app_version)s"
#define AppPublisher "%(app_name)s"
#define AppExeName   "%(exe_name)s"
#define SourceDir    "%(source_dir)s"

[Setup]
AppId={A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppVerName={#AppName} {#AppVersion}

; Detecta automáticamente el disco del SO (normalmente C:)
DefaultDirName={sd}\\abm-stock

; Muestra la pantalla de elección de carpeta destino
DisableDirPage=no

DefaultGroupName={#AppName}
AllowNoIcons=yes
OutputDir=%(builds_dir)s
OutputBaseFilename=ABMStock_Setup_v%(app_version)s
%(icon_line)s
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
UninstallDisplayIcon={app}\\{#AppExeName}
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";   Description: "Crear acceso directo en el Escritorio"; \\
      GroupDescription: "Accesos directos adicionales:"; Flags: unchecked
Name: "startmenuicon"; Description: "Crear acceso directo en el Menú Inicio"; \\
      GroupDescription: "Accesos directos adicionales:"

[Files]
; Copia todo el contenido compilado por PyInstaller
Source: "{#SourceDir}\\*"; DestDir: "{app}"; \\
        Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\\{#AppName}";             Filename: "{app}\\{#AppExeName}"
Name: "{group}\\Desinstalar {#AppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\\{#AppName}";     Filename: "{app}\\{#AppExeName}"; \\
      Tasks: desktopicon

[Run]
Filename: "{app}\\{#AppExeName}"; \\
          Description: "Iniciar {#AppName} ahora"; \\
          Flags: nowait postinstall skipifsilent

[Dirs]
; La carpeta images/ nunca se elimina al desinstalar (conserva el stock)
Name: "{app}\\images"; Flags: uninsneveruninstall
Name: "{app}\\assets"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\\__pycache__"
Type: filesandordirs; Name: "{app}\\build"
"""


# ── Búsqueda de Inno Setup ────────────────────────────────────────────────────

def find_inno_setup() -> str | None:
    """Busca ISCC.exe en las rutas más comunes y en el registro de Windows."""
    common_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe",
    ]
    for p in common_paths:
        if Path(p).exists():
            return p

    if not HAS_WINREG:
        return None

    reg_keys = [
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1"),
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1"),
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 5_is1"),
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 5_is1"),
    ]
    for hive, key_path in reg_keys:
        try:
            with winreg.OpenKey(hive, key_path) as key:
                location, _ = winreg.QueryValueEx(key, "InstallLocation")
                iscc = Path(location) / "ISCC.exe"
                if iscc.exists():
                    return str(iscc)
        except (FileNotFoundError, OSError):
            continue

    return None


# ── Generación del script ISS ─────────────────────────────────────────────────

def generate_iss(output_path: Path) -> None:
    icon_line = f"SetupIconFile={ICON_PATH}" if ICON_PATH.exists() else ""
    content = ISS_TEMPLATE % {
        "app_name":   APP_NAME,
        "app_version": APP_VERSION,
        "exe_name":   EXE_NAME,
        "source_dir": str(DIST_DIR),
        "builds_dir": str(BUILDS_DIR),
        "icon_line":  icon_line,
    }
    output_path.write_text(content, encoding="utf-8")


# ── Fallback: ZIP portable ─────────────────────────────────────────────────────

INSTALL_BAT = """\
@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

echo.
echo  ============================================
echo   ABM Stock v{version} - Instalacion
echo  ============================================
echo.

:: Detectar disco del sistema operativo
set DEST=!SystemDrive!\\abm-stock

:: Permitir ruta personalizada como primer argumento
if not "%~1"=="" set DEST=%~1

echo  Se instalara en: !DEST!
echo.
set /p CONFIRM=  Presiona ENTER para continuar o escribe una ruta diferente: 
if not "!CONFIRM!"=="" set DEST=!CONFIRM!

echo.
echo  Instalando en !DEST! ...
if not exist "!DEST!" mkdir "!DEST!"

xcopy /E /I /Y "%~dp0*" "!DEST!\\" >nul

echo.
echo  Instalacion completada.
echo  Ejecuta: !DEST!\\ABMStock.exe
echo.
pause
""".format(version=APP_VERSION)


def create_zip_fallback() -> Path:
    """Crea un ZIP portable que contiene los binarios + install.bat."""
    zip_path = BUILDS_DIR / f"ABMStock_v{APP_VERSION}_portable.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        # install.bat en la raíz del ZIP
        zf.writestr("install.bat", INSTALL_BAT)
        # todos los archivos compilados
        for file_path in DIST_DIR.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(DIST_DIR)
                zf.write(file_path, arcname)
    return zip_path


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    print()

    if not DIST_DIR.exists():
        print(f"  ERROR: {DIST_DIR} no existe.")
        print("         Ejecuta PyInstaller antes de llamar a este script.")
        return 1

    BUILDS_DIR.mkdir(exist_ok=True)

    inno = find_inno_setup()

    if inno:
        print(f"  Inno Setup encontrado: {inno}")
        iss_path = PROJECT_DIR / "_installer_script.iss"
        try:
            generate_iss(iss_path)
            print("  Script .iss generado.")

            result = subprocess.run(
                [inno, str(iss_path)],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                print("\n  ERROR al compilar con Inno Setup:")
                print(result.stdout[-3000:] if result.stdout else "")
                print(result.stderr[-1000:] if result.stderr else "")
                return 1

            installer = BUILDS_DIR / f"ABMStock_Setup_v{APP_VERSION}.exe"
            print(f"\n  Instalador creado:")
            print(f"  {installer}")
        finally:
            if iss_path.exists():
                iss_path.unlink()
    else:
        print("  Inno Setup no encontrado.")
        print("  Generando ZIP portable como alternativa...\n")
        zip_path = create_zip_fallback()
        print(f"  ZIP portable creado:")
        print(f"  {zip_path}")
        print()
        print("  NOTA: Para generar un instalador .exe en el futuro,")
        print("  instala Inno Setup (gratuito) y vuelve a ejecutar build.bat:")
        print("  https://jrsoftware.org/isdownload.php")

    return 0


if __name__ == "__main__":
    sys.exit(main())
