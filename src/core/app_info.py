"""
Información general de la aplicación: versión, desarrollador y soporte.

Este es el único archivo que hay que actualizar con cada release.
Los demás módulos (UI, build, instalador) leen sus datos desde aquí.
"""

# ── Versión ───────────────────────────────────────────────────────────────────

VERSION       = "1.0.0"
VERSION_MAJOR = 1
VERSION_MINOR = 0
VERSION_PATCH = 0
RELEASE_DATE  = "2026-03-17"      # ISO 8601
BUILD_STAGE   = "stable"          # alpha | beta | rc | stable

# ── Identidad de la aplicación ────────────────────────────────────────────────

APP_NAME        = "ABM Stock"
APP_DESCRIPTION = (
    "Sistema de gestión de inventario para negocios. "
    "Permite administrar el catálogo de productos, controlar stock, "
    "calcular precios con margen de ganancia y explorar el inventario "
    "mediante filtros y vistas personalizadas."
)

# ── Desarrollador y propietario ───────────────────────────────────────────────

DEVELOPER_NAME    = "Miguel Britos"            # <<< completar nombre completo
DEVELOPER_COMPANY = ""                  # <<< nombre empresa / marca (opcional)
DEVELOPER_EMAIL   = "miguelbritos91@gmail.com"                  # <<< email de contacto
DEVELOPER_WEBSITE = ""                  # <<< sitio web (opcional)
DEVELOPER_PHONE   = ""                  # <<< teléfono / WhatsApp (opcional)

# ── Soporte y reporte de errores ──────────────────────────────────────────────

SUPPORT_EMAIL   = DEVELOPER_EMAIL       # puede ser diferente al de contacto
SUPPORT_WEBSITE = DEVELOPER_WEBSITE
SUPPORT_MESSAGE = (
    "Para reportar errores o solicitar soporte técnico, "
    "por favor contactá al desarrollador indicando:\n"
    "  • Descripción del problema\n"
    "  • Pasos para reproducirlo\n"
    "  • Versión de la aplicación"
)

# ── Derechos de autor ─────────────────────────────────────────────────────────

COPYRIGHT_YEAR   = "2026"
COPYRIGHT_HOLDER = DEVELOPER_NAME
COPYRIGHT_TEXT   = f"© {COPYRIGHT_YEAR} {COPYRIGHT_HOLDER}. Todos los derechos reservados."

# ── Licencia ──────────────────────────────────────────────────────────────────

LICENSE_TYPE    = "MIT License (Open Source)"
LICENSE_SUMMARY = (
    "Este software se distribuye bajo la Licencia MIT. "
    "Se permite usar, copiar, modificar y distribuir el código "
    "siempre que se conserve el aviso de copyright original. "
    "El software se entrega 'tal cual', sin garantías de ningún tipo. "
    "El autor no se responsabiliza por pérdida de datos ni daños derivados del uso."
)

# ── Resumen para mostrar en la UI ─────────────────────────────────────────────

def get_full_version() -> str:
    suffix = f" ({BUILD_STAGE})" if BUILD_STAGE != "stable" else ""
    return f"v{VERSION}{suffix}"


def get_about_lines() -> dict:
    """Retorna un dict con todos los datos para renderizar en el modal About."""
    return {
        "app_name":    APP_NAME,
        "version":     get_full_version(),
        "release":     RELEASE_DATE,
        "description": APP_DESCRIPTION,
        "developer":   DEVELOPER_NAME,
        "company":     DEVELOPER_COMPANY,
        "email":       DEVELOPER_EMAIL or "—",
        "website":     DEVELOPER_WEBSITE or "—",
        "phone":       DEVELOPER_PHONE or "—",
        "support":     SUPPORT_EMAIL or DEVELOPER_EMAIL or "—",
        "copyright":   COPYRIGHT_TEXT,
        "license":     LICENSE_TYPE,
    }
