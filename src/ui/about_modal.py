"""
Modal "Acerca de ABM Stock".
Muestra datos del desarrollador, versión, soporte y licencia.
Lee toda la información desde src/core/app_info.py.
"""
import tkinter as tk
from tkinter import scrolledtext
from PIL import Image, ImageTk

from src.core import app_info as info
from src.core.config import ASSETS_DIR
from src.ui import styles as S


class AboutModal(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title(f"Acerca de {info.APP_NAME}")
        self.configure(bg=S.BG)
        self.resizable(False, False)
        self._build()
        self._center()
        self.grab_set()

    def _center(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w)//2}+{(sh - h)//2}")

    def _build(self):
        d = info.get_about_lines()

        # ── Header ────────────────────────────────────────────────────────
        header = tk.Frame(self, bg=S.PRIMARY, padx=24, pady=18)
        header.pack(fill="x")

        self._header_logo_img = self._load_logo(180)
        if self._header_logo_img:
            tk.Label(header, image=self._header_logo_img, bg=S.PRIMARY).pack(side="left", padx=(0, 14))
        else:
            tk.Label(
                header, text="👗",
                bg=S.PRIMARY, fg="white",
                font=(S.FONT_FAMILY, 32),
            ).pack(side="left", padx=(0, 14))

        title_col = tk.Frame(header, bg=S.PRIMARY)
        title_col.pack(side="left")
        tk.Label(
            title_col, text=d["app_name"],
            bg=S.PRIMARY, fg="white",
            font=(S.FONT_FAMILY, S.FONT_SIZE_TITLE, "bold"),
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            title_col, text=f"Versión {d['version']}  ·  {d['release']}",
            bg=S.PRIMARY, fg=S.PRIMARY_LIGHT,
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM),
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            title_col, text=d["copyright"],
            bg=S.PRIMARY, fg=S.PRIMARY_LIGHT,
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM),
            anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        # ── Cuerpo ────────────────────────────────────────────────────────
        body = tk.Frame(self, bg=S.BG, padx=24, pady=16)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)

        def _section(text):
            tk.Label(
                body, text=text,
                bg=S.BG_SIDEBAR, fg=S.PRIMARY_DARK,
                font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "bold"),
                anchor="w", padx=6, pady=3,
            ).grid(
                row=_section.row, column=0, columnspan=2,
                sticky="ew", pady=(12, 4),
            )
            _section.row += 1
        _section.row = 0

        def _row(label, value):
            if not value or value == "—":
                return
            tk.Label(
                body, text=label + ":",
                bg=S.BG, fg=S.TEXT_MEDIUM,
                font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "bold"),
                anchor="e",
            ).grid(row=_section.row, column=0, sticky="e", padx=(0, 10), pady=3)
            tk.Label(
                body, text=value,
                bg=S.BG, fg=S.TEXT_DARK,
                font=(S.FONT_FAMILY, S.FONT_SIZE_MD),
                anchor="w", wraplength=280, justify="left",
            ).grid(row=_section.row, column=1, sticky="w", pady=3)
            _section.row += 1

        # Descripción
        _section("Descripción")
        tk.Label(
            body, text=d["description"],
            bg=S.BG, fg=S.TEXT_MEDIUM,
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM),
            wraplength=400, justify="left", anchor="w",
        ).grid(row=_section.row, column=0, columnspan=2, sticky="w", pady=(0, 4))
        _section.row += 1

        # Desarrollador
        _section("Desarrollador")
        _row("Nombre",  d["developer"])
        _row("Empresa", d["company"])
        _row("Email",   d["email"])
        _row("Web",     d["website"])
        _row("Teléfono / WhatsApp", d["phone"])

        # Soporte
        _section("Soporte técnico")
        _row("Contacto", d["support"])
        tk.Label(
            body, text=info.SUPPORT_MESSAGE,
            bg=S.BG, fg=S.TEXT_MEDIUM,
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM),
            wraplength=400, justify="left", anchor="w",
        ).grid(row=_section.row, column=0, columnspan=2, sticky="w", pady=(0, 4))
        _section.row += 1

        # Licencia
        _section("Licencia")
        _row("Tipo", d["license"])
        tk.Label(
            body, text=info.LICENSE_SUMMARY,
            bg=S.BG, fg=S.TEXT_MEDIUM,
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM),
            wraplength=400, justify="left", anchor="w",
        ).grid(row=_section.row, column=0, columnspan=2, sticky="w", pady=(0, 4))
        _section.row += 1

        # Botón ver licencia completa
        tk.Button(
            body,
            text="Ver licencia completa…",
            bg=S.BG, fg=S.PRIMARY,
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "underline"),
            relief="flat", bd=0, cursor="hand2",
            command=self._show_license,
        ).grid(row=_section.row, column=0, columnspan=2, sticky="w", pady=(0, 6))
        _section.row += 1

        # ── Footer ────────────────────────────────────────────────────────
        footer = tk.Frame(self, bg=S.BG, pady=0)
        footer.pack(fill="x", padx=24, pady=(0, 16))

        tk.Button(
            footer, text="Cerrar",
            **S.BTN_PRIMARY, command=self.destroy,
        ).pack(side="right")

    def _load_logo(self, width: int):
        """Carga assets/icon.png redimensionado a `width` px manteniendo proporción."""
        try:
            icon_png = ASSETS_DIR / "icon.png"
            if icon_png.exists():
                img = Image.open(icon_png).convert("RGBA")
                h = int(width * img.height / img.width)
                img = img.resize((width, h), Image.LANCZOS)
                return ImageTk.PhotoImage(img)
        except Exception:
            pass
        return None

    def _show_license(self):
        """Abre una ventana secundaria con el texto completo de la licencia."""
        win = tk.Toplevel(self)
        win.title("Licencia de uso — ABM Stock")
        win.configure(bg=S.BG)
        win.geometry("660x520")
        win.grab_set()

        # Centrar
        win.update_idletasks()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"660x520+{(sw - 660)//2}+{(sh - 520)//2}")

        header = tk.Frame(win, bg=S.PRIMARY, padx=20, pady=10)
        header.pack(fill="x")
        tk.Label(
            header, text="Acuerdo de Licencia de Usuario Final (EULA)",
            bg=S.PRIMARY, fg="white",
            font=(S.FONT_FAMILY, S.FONT_SIZE_MD, "bold"),
        ).pack(anchor="w")

        txt = scrolledtext.ScrolledText(
            win,
            font=("Consolas", 8),
            bg="#FAFAFA", fg=S.TEXT_DARK,
            relief="flat", wrap="word",
            padx=14, pady=10,
        )
        txt.pack(fill="both", expand=True, padx=10, pady=(8, 4))

        try:
            from src.core.config import BASE_DIR
            license_path = BASE_DIR / "LICENSE"
            if license_path.exists():
                txt.insert("1.0", license_path.read_text(encoding="utf-8"))
            else:
                txt.insert("1.0", info.LICENSE_SUMMARY)
        except Exception:
            txt.insert("1.0", info.LICENSE_SUMMARY)

        txt.config(state="disabled")

        tk.Button(
            win, text="Cerrar",
            **S.BTN_PRIMARY, command=win.destroy,
        ).pack(side="right", padx=10, pady=(0, 10))
