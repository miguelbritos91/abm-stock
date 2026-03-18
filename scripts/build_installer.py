#!/usr/bin/env python3
"""
Genera el instalador de ABM Stock para Windows.

Prioridad:
  1. WiX 4  →  ABMStock_v<VERSION>.msi          (instalador MSI nativo)
  2. Inno Setup  →  ABMStock_Setup_v<VERSION>.exe  (fallback)
  3. ZIP portable  →  ABMStock_v<VERSION>_portable.zip  (fallback final)

WiX 4 se instala automáticamente como dotnet global tool si dotnet está disponible.
Invocado por build.bat en el paso 5/5.
"""
import hashlib
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

# ── Bootstrap de path ─────────────────────────────────────────────────────────

_PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(_PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(_PROJECT_DIR))

from src.core.app_info import APP_NAME, VERSION  # noqa: E402

try:
    import winreg
    HAS_WINREG = True
except ImportError:
    HAS_WINREG = False

# ── Constantes globales ───────────────────────────────────────────────────────

PROJECT_DIR = _PROJECT_DIR
DIST_DIR    = PROJECT_DIR / "dist" / "ABMStock"
BUILDS_DIR  = PROJECT_DIR / "builds"
ICON_PATH   = PROJECT_DIR / "assets" / "icon.ico"

APP_VERSION = VERSION
EXE_NAME    = "ABMStock.exe"

# GUID fijo: NO cambiar entre versiones — Windows lo usa para detectar upgrades/uninstall
UPGRADE_CODE = "A1B2C3D4-E5F6-7890-ABCD-EF1234567890"


# ═══════════════════════════════════════════════════════════════════════════════
#  WiX 4 — MSI nativo de Windows
# ═══════════════════════════════════════════════════════════════════════════════

# Texto de licencia mostrado en el wizard (RTF puro ASCII con escapes Latin-1)
_LICENSE_RTF = (
    r"{\rtf1\ansi\ansicpg1252\deff0"
    r"{\fonttbl{\f0\fnil\fcharset0 Segoe UI;}}"
    r"\f0\fs22\b " + APP_NAME + r"\b0\par\par"
    r"Software libre para gesti\'f3n de stock.\par\par"
    r"Puede instalar y usar este software de forma gratuita "
    r"para administraci\'f3n interna de inventario.\par}"
)


def _find_wix() -> "str | None":
    """Busca el CLI de WiX 4 en PATH y en rutas estándar de dotnet global tools."""
    for name in ("wix", "wix.exe"):
        try:
            r = subprocess.run([name, "--version"], capture_output=True, timeout=8)
            if r.returncode == 0:
                return name
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
    for base in (os.environ.get("USERPROFILE", ""), os.environ.get("LOCALAPPDATA", "")):
        for sub in (".dotnet/tools", "Microsoft/dotnet/tools"):
            p = Path(base) / sub / "wix.exe"
            if p.exists():
                return str(p)
    return None


def _ensure_wix() -> "str | None":
    """Retorna el path al CLI de WiX 4, instalándolo vía dotnet si es necesario."""
    wix = _find_wix()
    if wix:
        return wix
    try:
        r = subprocess.run(["dotnet", "--version"], capture_output=True, timeout=10)
        if r.returncode != 0:
            return None
    except FileNotFoundError:
        return None

    print("  dotnet disponible — instalando WiX 4 (puede demorar unos minutos)...")
    for args in (
        ["dotnet", "tool", "install", "--global", "wix"],
        ["dotnet", "tool", "update",  "--global", "wix"],
    ):
        r = subprocess.run(args, capture_output=True, text=True, timeout=180)
        if r.returncode == 0:
            break
    return _find_wix()


def _wix_id(rel: str, prefix: str = "c") -> str:
    """Crea un ID WiX válido (A-Z a-z 0-9 _) de máximo 72 caracteres.

    Siempre incluye un hash MD5 del path original para evitar colisiones
    entre archivos cuyo nombre difiere solo en caracteres especiales
    (p. ej. tzdata/Etc/GMT+3 vs tzdata/Etc/GMT-3 → ambos sanitizan a GMT_3).
    """
    h = hashlib.md5(rel.encode()).hexdigest()[:8]
    safe = re.sub(r"[^A-Za-z0-9]", "_", rel)
    if safe[:1].isdigit():
        safe = "_" + safe
    candidate = f"{prefix}_{safe}_{h}"
    if len(candidate) <= 72:
        return candidate
    return f"{prefix}_{safe[:54]}_{h}"


def _norm_version(v: str) -> str:
    """Normaliza a major.minor.patch.build exigido por MSI."""
    parts = re.sub(r"[^0-9.]", ".", v).split(".")
    nums  = [re.sub(r"\D", "0", p) or "0" for p in parts if p]
    while len(nums) < 4:
        nums.append("0")
    return ".".join(nums[:4])


def _generate_wxs(wxs_path: Path, rtf_path: Path) -> None:
    """Genera un .wxs completo para el bundle PyInstaller con wizard de instalación."""
    all_files = sorted(f for f in DIST_DIR.rglob("*") if f.is_file())

    # Mapa subpath → ID WiX para cada directorio
    dir_ids: dict[str, str] = {"": "INSTALLFOLDER"}
    for f in all_files:
        parts = f.relative_to(DIST_DIR).parts[:-1]
        for i in range(len(parts)):
            key = "/".join(parts[: i + 1])
            if key not in dir_ids:
                dir_ids[key] = _wix_id(key, "d")

    # Agrupar archivos por directorio
    by_dir: dict[str, list[Path]] = {}
    for f in all_files:
        rel = f.relative_to(DIST_DIR)
        dk  = "/".join(rel.parts[:-1])
        by_dir.setdefault(dk, []).append(f)

    X: list[str] = []

    X += [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<Wix xmlns="http://wixtoolset.org/schemas/v4/wxs"',
        '     xmlns:ui="http://wixtoolset.org/schemas/v4/wxs/ui">',
        '',
        f'  <Package Name="{xml_escape(APP_NAME)}"',
        f'           Manufacturer="{xml_escape(APP_NAME)}"',
        f'           Version="{_norm_version(APP_VERSION)}"',
        f'           UpgradeCode="{{{UPGRADE_CODE}}}"',
        '           Language="3082"',
        '           InstallerVersion="500">',
        '',
    ]

    if ICON_PATH.exists():
        X += [
            f'    <Icon Id="AppIcon" SourceFile="{ICON_PATH}" />',
            '    <Property Id="ARPPRODUCTICON" Value="AppIcon" />',
        ]

    X += [
        '    <MajorUpgrade',
        '        DowngradeErrorMessage="Ya existe una versi&#xF3;n m&#xE1;s nueva instalada." />',
        '    <MediaTemplate EmbedCab="yes" CompressionLevel="high" />',
        '',
        '    <!-- Wizard con selector de carpeta destino -->',
        '    <ui:WixUI Id="WixUI_InstallDir" />',
        '    <Property Id="WIXUI_INSTALLDIR" Value="INSTALLFOLDER" />',
        f'    <WixVariable Id="WixUILicenseRtf" Value="{rtf_path}" Overridable="yes" />',
        '',
        f'    <Feature Id="Main" Title="{xml_escape(APP_NAME)}" Level="1">',
    ]

    for dk, files in sorted(by_dir.items()):
        for f in files:
            rel = f.relative_to(DIST_DIR)
            X.append(f'      <ComponentRef Id="{_wix_id(str(rel))}" />')
    X += [
        '      <ComponentRef Id="cmp_StartMenu" />',
        '      <ComponentRef Id="cmp_Desktop" />',
        '    </Feature>',
        '',
    ]

    # Árbol de directorios
    X.append('    <StandardDirectory Id="ProgramFiles6432Folder">')
    X.append(f'      <Directory Id="INSTALLFOLDER" Name="{xml_escape(APP_NAME)}">')

    def _dir_children(parent: str, indent: int) -> None:
        kids = sorted(k for k in dir_ids if k and "/".join(k.split("/")[:-1]) == parent)
        for k in kids:
            name = k.split("/")[-1]
            X.append(" " * indent + f'<Directory Id="{dir_ids[k]}" Name="{xml_escape(name)}">')
            _dir_children(k, indent + 2)
            X.append(" " * indent + "</Directory>")

    _dir_children("", 8)
    X += [
        '      </Directory>',
        '    </StandardDirectory>',
        '',
        '    <StandardDirectory Id="ProgramMenuFolder">',
        f'      <Directory Id="AppMenuFolder" Name="{xml_escape(APP_NAME)}" />',
        '    </StandardDirectory>',
        '    <StandardDirectory Id="DesktopFolder" />',
        '',
    ]

    # Componentes de archivos
    for dk, files in sorted(by_dir.items()):
        dir_id = dir_ids[dk]
        for f in files:
            rel = f.relative_to(DIST_DIR)
            cid = _wix_id(str(rel))
            fid = _wix_id(str(rel), "f")
            X += [
                f'    <Component Id="{cid}" Directory="{dir_id}">',
                f'      <File Id="{fid}" Source="{f}" KeyPath="yes" />',
                '    </Component>',
            ]

    # Accesos directos — Menú Inicio
    X += [
        '',
        '    <Component Id="cmp_StartMenu" Directory="AppMenuFolder">',
        '      <Shortcut Id="sc_StartMenu"',
        f'               Name="{xml_escape(APP_NAME)}"',
        f'               Target="[INSTALLFOLDER]{EXE_NAME}"',
        '               WorkingDirectory="INSTALLFOLDER"',
        '               Advertise="no" />',
        '      <Shortcut Id="sc_Uninstall"',
        f'               Name="Desinstalar {xml_escape(APP_NAME)}"',
        '               Target="[System64Folder]msiexec.exe"',
        '               Arguments="/x [ProductCode]"',
        '               Advertise="no" />',
        '      <RemoveFolder Id="rmAppMenuFolder" On="uninstall" />',
        '      <RegistryValue Root="HKCU"',
        '                    Key="Software\\ABMStock\\StartMenu"',
        '                    Name="installed" Type="integer" Value="1"',
        '                    KeyPath="yes" />',
        '    </Component>',
        '',
        '    <!-- Acceso directo en el Escritorio -->',
        '    <Component Id="cmp_Desktop" Directory="DesktopFolder">',
        '      <Shortcut Id="sc_Desktop"',
        f'               Name="{xml_escape(APP_NAME)}"',
        f'               Target="[INSTALLFOLDER]{EXE_NAME}"',
        '               WorkingDirectory="INSTALLFOLDER"',
        '               Advertise="no" />',
        '      <RegistryValue Root="HKCU"',
        '                    Key="Software\\ABMStock\\Desktop"',
        '                    Name="installed" Type="integer" Value="1"',
        '                    KeyPath="yes" />',
        '    </Component>',
        '',
        '  </Package>',
        '</Wix>',
    ]

    wxs_path.write_text("\n".join(X), encoding="utf-8")


def _build_msi(wix: str) -> "Path | None":
    """Instala extensión UI de WiX, genera WXS y compila el MSI."""
    wxs_path = PROJECT_DIR / "_abmstock.wxs"
    rtf_path = PROJECT_DIR / "_license.rtf"
    msi_path = BUILDS_DIR / f"ABMStock_v{APP_VERSION}.msi"

    # Detectar versión mayor de WiX para instalar la extensión compatible
    rv = subprocess.run([wix, "--version"], capture_output=True, text=True, timeout=10)
    wix_major = "6"
    if rv.returncode == 0:
        ver_part = rv.stdout.strip().split(".")[0]
        if ver_part.isdigit():
            wix_major = ver_part
    ext_name = "WixToolset.UI.wixext"
    print(f"  WiX v{wix_major} detectado — instalando extensión {ext_name}/{wix_major}.x...")

    ext_ok = False
    for ext_spec in (f"{ext_name}/{wix_major}.0.0", ext_name):
        for scope_flag in (["--global"], []):
            r = subprocess.run(
                [wix, "extension", "add"] + scope_flag + [ext_spec],
                capture_output=True, text=True, timeout=120,
            )
            if r.returncode == 0:
                ext_ok = True
                break
        if ext_ok:
            break
        print(f"  (intento {ext_spec}): {(r.stdout + r.stderr).strip()[-200:]}")
    if not ext_ok:
        print("  ADVERTENCIA: no se pudo instalar WixToolset.UI.wixext — se omite WiX 4.")
        return None

    # RTF mínimo requerido por el wizard WixUI_InstallDir
    rtf_path.write_bytes(_LICENSE_RTF.encode("latin-1"))

    try:
        print("  Generando WXS...")
        _generate_wxs(wxs_path, rtf_path)

        print(f"  Compilando ABMStock_v{APP_VERSION}.msi  (puede demorar)...")
        result = subprocess.run(
            [
                wix, "build", str(wxs_path),
                "-ext", ext_name,
                "-o", str(msi_path),
            ],
            capture_output=True, text=True,
            cwd=str(PROJECT_DIR), timeout=300,
        )

        if result.returncode != 0:
            print("\n  ERROR al compilar el MSI:")
            if result.stdout:
                print(result.stdout[-4000:])
            if result.stderr:
                print(result.stderr[-1000:])
            return None

        return msi_path

    finally:
        for tmp in (wxs_path, rtf_path):
            if tmp.exists():
                tmp.unlink()


# ═══════════════════════════════════════════════════════════════════════════════
#  WiX 3 — binaries standalone, sin .NET (auto-descarga ~17 MB)
# ═══════════════════════════════════════════════════════════════════════════════

WIX3_URL    = "https://github.com/wixtoolset/wix3/releases/download/wix3141rtm/wix314-binaries.zip"
WIX3_DIR    = PROJECT_DIR / "tools" / "wix3"
WIX3_CANDLE = WIX3_DIR / "candle.exe"
WIX3_LIGHT  = WIX3_DIR / "light.exe"
WIX3_EXT_UI = WIX3_DIR / "WixUIExtension.dll"


def _find_wix3() -> "tuple[str, str] | None":
    """Retorna (candle, light) si WiX 3 está ya disponible en caché o en PATH."""
    if WIX3_CANDLE.exists() and WIX3_LIGHT.exists():
        return str(WIX3_CANDLE), str(WIX3_LIGHT)
    for d in os.environ.get("PATH", "").split(os.pathsep):
        c, lx = Path(d) / "candle.exe", Path(d) / "light.exe"
        if c.exists() and lx.exists():
            return str(c), str(lx)
    return None


def _download_wix3() -> "tuple[str, str] | None":
    """Descarga WiX 3 binaries desde GitHub (~17 MB) y los extrae en tools/wix3/."""
    import urllib.request
    import zipfile as zf

    print("  Descargando WiX 3 binaries (~17 MB, solo la primera vez)...")
    WIX3_DIR.mkdir(parents=True, exist_ok=True)
    zip_dest = WIX3_DIR / "wix3-binaries.zip"
    try:
        req = urllib.request.Request(WIX3_URL, headers={"User-Agent": "ABMStock-build/1.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            zip_dest.write_bytes(resp.read())
    except Exception as e:
        print(f"  ERROR al descargar WiX 3: {e}")
        return None

    try:
        with zf.ZipFile(zip_dest) as z:
            extracted = 0
            for member in z.namelist():
                name = Path(member).name
                # Extraer TODOS los .exe y .dll — candle.exe necesita wix.dll y otros ensamblados
                if name and Path(name).suffix.lower() in {".exe", ".dll"}:
                    (WIX3_DIR / name).write_bytes(z.read(member))
                    extracted += 1
            print(f"  Extraídos {extracted} archivos de WiX 3.")
    except Exception as e:
        print(f"  ERROR al extraer WiX 3: {e}")
        return None
    finally:
        if zip_dest.exists():
            zip_dest.unlink()

    return _find_wix3()


def _generate_wix3_wxs(wxs_path: Path, rtf_path: Path) -> None:
    """Genera un .wxs compatible con WiX 3 (schema 2006/wi)."""
    all_files = sorted(f for f in DIST_DIR.rglob("*") if f.is_file())

    dir_ids: dict[str, str] = {"": "INSTALLFOLDER"}
    for f in all_files:
        parts = f.relative_to(DIST_DIR).parts[:-1]
        for i in range(len(parts)):
            key = "/".join(parts[: i + 1])
            if key not in dir_ids:
                dir_ids[key] = _wix_id(key, "d")

    by_dir: dict[str, list[Path]] = {}
    for f in all_files:
        rel = f.relative_to(DIST_DIR)
        dk  = "/".join(rel.parts[:-1])
        by_dir.setdefault(dk, []).append(f)

    X: list[str] = []
    X += [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">',
        '',
        f'  <Product Id="*"',
        f'           Name="{xml_escape(APP_NAME)}"',
        f'           Language="3082"',
        f'           Version="{_norm_version(APP_VERSION)}"',
        f'           Manufacturer="{xml_escape(APP_NAME)}"',
        f'           UpgradeCode="{{{UPGRADE_CODE}}}">',
        '',
        '    <Package InstallerVersion="500" Compressed="yes" InstallScope="perMachine" />',
        '',
    ]
    if ICON_PATH.exists():
        X += [
            f'    <Icon Id="AppIcon.ico" SourceFile="{ICON_PATH}" />',
            '    <Property Id="ARPPRODUCTICON" Value="AppIcon.ico" />',
            '',
        ]
    X += [
        '    <MajorUpgrade',
        '        DowngradeErrorMessage="Ya existe una versi&#xF3;n m&#xE1;s nueva instalada." />',
        '    <MediaTemplate EmbedCab="yes" CompressionLevel="high" />',
        '',
        '    <UIRef Id="WixUI_InstallDir" />',
        '    <Property Id="WIXUI_INSTALLDIR" Value="INSTALLFOLDER" />',
        f'    <WixVariable Id="WixUILicenseRtf" Value="{rtf_path}" />',
        '',
        f'    <Feature Id="ProductFeature" Title="{xml_escape(APP_NAME)}" Level="1">',
        '      <ComponentGroupRef Id="AppFiles" />',
        '      <ComponentRef Id="cmp_StartMenu" />',
        '      <ComponentRef Id="cmp_Desktop" />',
        '    </Feature>',
        '',
        '  </Product>',
        '',
        '  <Fragment>',
        '    <Directory Id="TARGETDIR" Name="SourceDir">',
        '      <Directory Id="ProgramFiles64Folder">',
        f'        <Directory Id="INSTALLFOLDER" Name="{xml_escape(APP_NAME)}">',
    ]

    def _wix3_dir_children(parent: str, indent: int) -> None:
        kids = sorted(k for k in dir_ids if k and "/".join(k.split("/")[:-1]) == parent)
        for k in kids:
            name = k.split("/")[-1]
            X.append(" " * indent + f'<Directory Id="{dir_ids[k]}" Name="{xml_escape(name)}">')
            _wix3_dir_children(k, indent + 2)
            X.append(" " * indent + "</Directory>")

    _wix3_dir_children("", 10)

    X += [
        '        </Directory>',
        '      </Directory>',
        '      <Directory Id="ProgramMenuFolder">',
        f'        <Directory Id="AppMenuFolder" Name="{xml_escape(APP_NAME)}" />',
        '      </Directory>',
        '      <Directory Id="DesktopFolder" />',
        '    </Directory>',
        '  </Fragment>',
        '',
        '  <Fragment>',
        '    <ComponentGroup Id="AppFiles">',
    ]

    for dk, files in sorted(by_dir.items()):
        dir_id = dir_ids[dk]
        for f in files:
            rel = f.relative_to(DIST_DIR)
            cid = _wix_id(str(rel))
            fid = _wix_id(str(rel), "f")
            X += [
                f'      <Component Id="{cid}" Directory="{dir_id}" Guid="*">',
                f'        <File Id="{fid}" Source="{f}" KeyPath="yes" />',
                '      </Component>',
            ]

    X += [
        '    </ComponentGroup>',
        '',
        '    <Component Id="cmp_StartMenu" Directory="AppMenuFolder" Guid="*">',
        '      <Shortcut Id="sc_StartMenu"',
        f'               Name="{xml_escape(APP_NAME)}"',
        f'               Target="[INSTALLFOLDER]{EXE_NAME}"',
        '               WorkingDirectory="INSTALLFOLDER" />',
        '      <Shortcut Id="sc_Uninstall"',
        f'               Name="Desinstalar {xml_escape(APP_NAME)}"',
        '               Target="[System64Folder]msiexec.exe"',
        '               Arguments="/x [ProductCode]" />',
        '      <RemoveFolder Id="rmAppMenuFolder" On="uninstall" />',
        '      <RegistryValue Root="HKCU"',
        '                    Key="Software\\ABMStock\\StartMenu"',
        '                    Name="installed" Type="integer" Value="1"',
        '                    KeyPath="yes" />',
        '    </Component>',
        '',
        '    <Component Id="cmp_Desktop" Directory="DesktopFolder" Guid="*">',
        '      <Shortcut Id="sc_Desktop"',
        f'               Name="{xml_escape(APP_NAME)}"',
        f'               Target="[INSTALLFOLDER]{EXE_NAME}"',
        '               WorkingDirectory="INSTALLFOLDER" />',
        '      <RegistryValue Root="HKCU"',
        '                    Key="Software\\ABMStock\\Desktop"',
        '                    Name="installed" Type="integer" Value="1"',
        '                    KeyPath="yes" />',
        '    </Component>',
        '',
        '  </Fragment>',
        '</Wix>',
    ]

    wxs_path.write_text("\n".join(X), encoding="utf-8")


def _build_msi_wix3(candle: str, light: str) -> "Path | None":
    """Compila MSI con WiX 3: candle.exe (.wxs→.wixobj) luego light.exe (.wixobj→.msi)."""
    wxs_path    = PROJECT_DIR / "_abmstock_v3.wxs"
    wixobj_path = PROJECT_DIR / "_abmstock_v3.wixobj"
    rtf_path    = PROJECT_DIR / "_license.rtf"
    msi_path    = BUILDS_DIR / f"ABMStock_v{APP_VERSION}.msi"

    ui_ext = str(WIX3_EXT_UI) if WIX3_EXT_UI.exists() else "WixUIExtension"
    rtf_path.write_bytes(_LICENSE_RTF.encode("latin-1"))

    try:
        print("  Generando WXS (WiX 3)...")
        _generate_wix3_wxs(wxs_path, rtf_path)

        print("  candle.exe: compilando WXS → WIXOBJ...")
        r1 = subprocess.run(
            [candle, str(wxs_path), "-ext", ui_ext, "-o", str(wixobj_path), "-arch", "x64"],
            capture_output=True, text=True, timeout=120,
        )
        if r1.returncode != 0:
            print("\n  ERROR en candle.exe:")
            print((r1.stdout or "")[-3000:])
            print((r1.stderr or "")[-1000:])
            return None

        print(f"  light.exe: linkeando → ABMStock_v{APP_VERSION}.msi...")
        r2 = subprocess.run(
            [light, str(wixobj_path), "-ext", ui_ext, "-spdb", "-o", str(msi_path)],
            capture_output=True, text=True, timeout=300,
        )
        if r2.returncode != 0:
            print("\n  ERROR en light.exe:")
            print((r2.stdout or "")[-3000:])
            print((r2.stderr or "")[-1000:])
            return None

        return msi_path

    finally:
        for tmp in (wxs_path, wixobj_path, rtf_path):
            if tmp.exists():
                tmp.unlink()


# ═══════════════════════════════════════════════════════════════════════════════
#  Inno Setup — EXE installer (fallback)
# ═══════════════════════════════════════════════════════════════════════════════

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
DefaultDirName={sd}\\abm-stock
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
Name: "desktopicon"; Description: "Crear acceso directo en el Escritorio"; \\
      GroupDescription: "Accesos directos:"; Flags: unchecked

[Files]
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
Name: "{app}\\images"; Flags: uninsneveruninstall
Name: "{app}\\assets"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\\__pycache__"
Type: filesandordirs; Name: "{app}\\build"
"""


def find_inno_setup() -> "str | None":
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


def generate_iss(output_path: Path) -> None:
    icon_line = f"SetupIconFile={ICON_PATH}" if ICON_PATH.exists() else ""
    content = ISS_TEMPLATE % {
        "app_name":    APP_NAME,
        "app_version": APP_VERSION,
        "exe_name":    EXE_NAME,
        "source_dir":  str(DIST_DIR),
        "builds_dir":  str(BUILDS_DIR),
        "icon_line":   icon_line,
    }
    output_path.write_text(content, encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════════
#  ZIP portable — fallback final
# ═══════════════════════════════════════════════════════════════════════════════

INSTALL_BAT = """\
@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
echo.
echo  ============================================
echo   ABM Stock v{version} - Instalacion
echo  ============================================
echo.
set DEST=!SystemDrive!\\abm-stock
echo  Se instalara en: !DEST!
set /p CONFIRM=  Presiona ENTER para continuar o escribe otra ruta: 
if not "!CONFIRM!"=="" set DEST=!CONFIRM!
echo.
echo  Instalando en !DEST! ...
if not exist "!DEST!" mkdir "!DEST!"
xcopy /E /I /Y "%~dp0*" "!DEST!\\" >nul
echo.
echo  Hecho. Ejecuta: !DEST!\\ABMStock.exe
echo.
pause
""".format(version=APP_VERSION)


def create_zip_fallback() -> Path:
    zip_path = BUILDS_DIR / f"ABMStock_v{APP_VERSION}_portable.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        zf.writestr("install.bat", INSTALL_BAT)
        for file_path in DIST_DIR.rglob("*"):
            if file_path.is_file():
                zf.write(file_path, file_path.relative_to(DIST_DIR))
    return zip_path


# ═══════════════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    print()

    if not DIST_DIR.exists():
        print(f"  ERROR: {DIST_DIR} no existe.")
        print("         Ejecuta PyInstaller antes de llamar a este script.")
        return 1

    BUILDS_DIR.mkdir(exist_ok=True)

    # ── 1. WiX 4 MSI ─────────────────────────────────────────────────────────
    print("  Buscando WiX 4...")
    wix = _ensure_wix()

    if wix:
        print(f"  WiX 4 encontrado: {wix}")
        msi = _build_msi(wix)
        if msi and msi.exists():
            print(f"\n  MSI generado exitosamente:")
            print(f"  {msi}")
            print()
            return 0
        print("\n  ADVERTENCIA: WiX 4 falló.")

    # ── 2. WiX 3 MSI (binaries standalone, sin .NET) ─────────────────────────
    print("  Buscando WiX 3 (o descargando ~17 MB la primera vez)...")
    wix3 = _find_wix3() or _download_wix3()
    if wix3:
        candle, light = wix3
        print(f"  WiX 3 encontrado: {candle}")
        msi = _build_msi_wix3(candle, light)
        if msi and msi.exists():
            print(f"\n  MSI generado exitosamente:")
            print(f"  {msi}")
            print()
            return 0
        print("\n  ADVERTENCIA: WiX 3 falló.")
    else:
        print("  No se pudo obtener WiX 3.")

    # ── 3. Inno Setup EXE ────────────────────────────────────────────────────
    inno = find_inno_setup()
    if inno:
        print(f"  Inno Setup encontrado: {inno}")
        iss_path = PROJECT_DIR / "_installer_script.iss"
        try:
            generate_iss(iss_path)
            result = subprocess.run([inno, str(iss_path)], capture_output=True, text=True)
            if result.returncode != 0:
                print("\n  ERROR Inno Setup:")
                print((result.stdout or "")[-3000:])
                print((result.stderr or "")[-1000:])
            else:
                exe = BUILDS_DIR / f"ABMStock_Setup_v{APP_VERSION}.exe"
                print(f"\n  Instalador EXE generado:")
                print(f"  {exe}")
                print()
                return 0
        finally:
            if iss_path.exists():
                iss_path.unlink()

    # ── 4. ZIP portable ───────────────────────────────────────────────────────
    print("  Ningún empaquetador disponible — generando ZIP portable...\n")
    zip_path = create_zip_fallback()
    print(f"  ZIP portable generado:")
    print(f"  {zip_path}")
    print()
    print("  NOTA: WiX 3 se descarga automáticamente si hay conexión a internet.")
    print("        Si la descarga falla, instala WiX 4 con .NET SDK:")
    print("        https://dotnet.microsoft.com/download")
    return 0


if __name__ == "__main__":
    sys.exit(main())

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


if __name__ == "__main__":
    sys.exit(main())
