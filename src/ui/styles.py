# Paleta de colores y estilos generales

PRIMARY      = "#1565C0"         # Azul fuerte
PRIMARY_DARK = "#0D47A1"         # Azul oscuro
PRIMARY_LIGHT = "#90CAF9"        # Azul claro
ACCENT       = "#2979FF"         # Azul acento
BG           = "#F3F7FF"         # Fondo general suave azulado
BG_CARD      = "#FFFFFF"
BG_SIDEBAR   = "#E3EAF8"         # Sidebar azul muy suave
TEXT_DARK    = "#212121"
TEXT_MEDIUM  = "#616161"
TEXT_LIGHT   = "#9E9E9E"
BORDER       = "#BBDEFB"         # Borde azul pastel
SUCCESS      = "#43A047"
DANGER       = "#E53935"
WARNING      = "#FB8C00"

FONT_FAMILY = "Segoe UI"
FONT_SIZE_SM = 9
FONT_SIZE_MD = 10
FONT_SIZE_LG = 12
FONT_SIZE_XL = 14
FONT_SIZE_TITLE = 18

BTN_PRIMARY = {
    "bg": PRIMARY,
    "fg": "white",
    "font": (FONT_FAMILY, FONT_SIZE_MD, "bold"),
    "relief": "flat",
    "cursor": "hand2",
    "padx": 14,
    "pady": 6,
    "bd": 0,
}

BTN_SECONDARY = {
    "bg": BG_SIDEBAR,
    "fg": PRIMARY_DARK,
    "font": (FONT_FAMILY, FONT_SIZE_MD),
    "relief": "flat",
    "cursor": "hand2",
    "padx": 14,
    "pady": 6,
    "bd": 0,
}

BTN_DANGER = {
    "bg": DANGER,
    "fg": "white",
    "font": (FONT_FAMILY, FONT_SIZE_MD),
    "relief": "flat",
    "cursor": "hand2",
    "padx": 10,
    "pady": 4,
    "bd": 0,
}

BTN_SUCCESS = {
    "bg": SUCCESS,
    "fg": "white",
    "font": (FONT_FAMILY, FONT_SIZE_MD),
    "relief": "flat",
    "cursor": "hand2",
    "padx": 10,
    "pady": 4,
    "bd": 0,
}

ENTRY_STYLE = {
    "bg": "white",
    "fg": TEXT_DARK,
    "font": (FONT_FAMILY, FONT_SIZE_MD),
    "relief": "solid",
    "bd": 1,
    "highlightthickness": 1,
    "highlightcolor": PRIMARY,
    "highlightbackground": BORDER,
}

LABEL_TITLE = {
    "bg": BG,
    "fg": PRIMARY_DARK,
    "font": (FONT_FAMILY, FONT_SIZE_TITLE, "bold"),
}

LABEL_SUBTITLE = {
    "bg": BG,
    "fg": TEXT_MEDIUM,
    "font": (FONT_FAMILY, FONT_SIZE_LG),
}


def fmt_moneda(value: float) -> str:
    """Formatea un importe con separador de miles (.) y decimales (,). Ej: $28.376,70"""
    formatted = f"{value:,.2f}"               # "28,376.70"
    formatted = formatted.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"${formatted}"
