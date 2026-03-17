"""
Ventana principal de la aplicación.
Construye el sidebar de navegación y gestiona el cambio entre secciones.
"""
import tkinter as tk

from src.core.database import init_db
from src.core import app_info as info
from src.ui import styles as S
from src.ui.home_section import HomeSection
from src.ui.products_section import ProductsSection
from src.ui.clientes_section import ClientesSection
from src.ui.venta_section import VentaSection
from src.ui.historial_ventas_section import HistorialVentasSection
from src.ui.about_modal import AboutModal


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        init_db()
        self.title(f"{info.APP_NAME} {info.get_full_version()}")
        self.geometry("1200x720")
        self.minsize(900, 600)
        self.configure(bg=S.BG)
        self._set_icon()
        self._build()

    def _set_icon(self):
        from src.core.config import ASSETS_DIR
        # Prioridad 1: icon.ico
        try:
            icon_path = ASSETS_DIR / "icon.ico"
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
                return
        except Exception:
            pass
        # Prioridad 2: icon.png como wm_iconphoto
        try:
            from PIL import Image, ImageTk
            icon_png = ASSETS_DIR / "icon.png"
            if icon_png.exists():
                img = Image.open(icon_png).convert("RGBA")
                img.thumbnail((64, 64), Image.LANCZOS)
                self._icon_img = ImageTk.PhotoImage(img)
                self.wm_iconphoto(True, self._icon_img)
        except Exception:
            pass

    def _build(self):
        main = tk.Frame(self, bg=S.BG)
        main.pack(fill="both", expand=True)

        # Inicializar antes de _build_sidebar para que pueda usarlos
        self._nav_buttons: dict[str, tk.Button] = {}
        self._active_section: str = ""

        # Sidebar
        sidebar = tk.Frame(main, bg=S.BG_SIDEBAR, width=190)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        self._build_sidebar(sidebar)

        # Área de contenido
        self.content = tk.Frame(main, bg=S.BG)
        self.content.pack(side="left", fill="both", expand=True)

        # Instanciar secciones
        self._sections: dict[str, tk.Frame] = {
            "home":      HomeSection(self.content),
            "products":  ProductsSection(self.content),
            "clientes":  ClientesSection(self.content),
            "ventas":    VentaSection(self.content),
            "historial": HistorialVentasSection(self.content),
        }
        self._show_section("home")

    def _build_sidebar(self, sidebar: tk.Frame):
        # Logo
        logo = tk.Frame(sidebar, bg=S.PRIMARY, pady=12)
        logo.pack(fill="x")
        self._sidebar_logo_img = self._load_logo(162)
        if self._sidebar_logo_img:
            tk.Label(logo, image=self._sidebar_logo_img, bg=S.PRIMARY).pack(padx=14, pady=(0, 4))
        else:
            tk.Label(logo, text="👗", bg=S.PRIMARY, fg="white", font=(S.FONT_FAMILY, 28)).pack()
            tk.Label(logo, text="ABM Stock", bg=S.PRIMARY, fg="white",
                     font=(S.FONT_FAMILY, S.FONT_SIZE_LG, "bold")).pack()
        tk.Label(logo, text="Gestión de Inventario", bg=S.PRIMARY, fg=S.PRIMARY_LIGHT,
                 font=(S.FONT_FAMILY, S.FONT_SIZE_SM)).pack()

        tk.Frame(sidebar, bg=S.BORDER, height=1).pack(fill="x", pady=(10, 0))

        # Ítems de navegación
        nav_items = [
            ("home",      "🏠  Inicio"),
            ("products",  "📦  Productos"),
            ("clientes",  "👥  Clientes"),
            ("ventas",    "🛒  Ventas"),
            ("historial", "📋  Historial"),
        ]
        nav_frame = tk.Frame(sidebar, bg=S.BG_SIDEBAR)
        nav_frame.pack(fill="x", pady=(8, 0))

        for key, label in nav_items:
            btn = tk.Button(
                nav_frame, text=label,
                bg=S.BG_SIDEBAR, fg=S.PRIMARY_DARK,
                activebackground=S.PRIMARY_LIGHT, activeforeground=S.PRIMARY_DARK,
                font=(S.FONT_FAMILY, S.FONT_SIZE_MD),
                relief="flat", bd=0, anchor="w",
                padx=20, pady=12, cursor="hand2",
                command=lambda k=key: self._show_section(k),
            )
            btn.pack(fill="x")
            self._nav_buttons[key] = btn

        # Botón Acerca de + versión al pie
        tk.Frame(sidebar, bg=S.BORDER, height=1).pack(fill="x", side="bottom", pady=(0, 0))
        tk.Label(
            sidebar,
            text=info.get_full_version(),
            bg=S.BG_SIDEBAR, fg=S.TEXT_LIGHT,
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM),
        ).pack(side="bottom", pady=(0, 6))
        tk.Button(
            sidebar,
            text="ℹ  Acerca de",
            bg=S.BG_SIDEBAR, fg=S.TEXT_MEDIUM,
            activebackground=S.PRIMARY_LIGHT, activeforeground=S.PRIMARY_DARK,
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM),
            relief="flat", bd=0, anchor="w",
            padx=20, pady=10, cursor="hand2",
            command=lambda: AboutModal(self),
        ).pack(fill="x", side="bottom")

    def _load_logo(self, width: int):
        """Carga assets/icon.png redimensionado a `width` px manteniendo proporción."""
        try:
            from PIL import Image, ImageTk
            from src.core.config import ASSETS_DIR
            icon_png = ASSETS_DIR / "icon.png"
            if icon_png.exists():
                img = Image.open(icon_png).convert("RGBA")
                h = int(width * img.height / img.width)
                img = img.resize((width, h), Image.LANCZOS)
                return ImageTk.PhotoImage(img)
        except Exception:
            pass
        return None

    def _show_section(self, key: str):
        if self._active_section == key:
            return

        for section in self._sections.values():
            section.pack_forget()

        section = self._sections[key]
        section.pack(fill="both", expand=True)

        if hasattr(section, "refresh"):
            section.refresh()

        self._active_section = key

        for k, btn in self._nav_buttons.items():
            btn.config(
                bg=S.PRIMARY if k == key else S.BG_SIDEBAR,
                fg="white"    if k == key else S.PRIMARY_DARK,
            )
