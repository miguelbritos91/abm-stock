"""
Widgets y utilidades reutilizables.
"""
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from src.ui import styles as S


def make_scrollable_frame(parent, bg=None):
    """Retorna (outer_frame, canvas, inner_frame). El inner_frame es scrollable."""
    bg = bg or S.BG
    outer = tk.Frame(parent, bg=bg)
    canvas = tk.Canvas(outer, bg=bg, highlightthickness=0)
    scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    inner = tk.Frame(canvas, bg=bg)

    inner.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
    )
    canvas_window = canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    # Expandir inner al ancho del canvas
    def _on_canvas_configure(event):
        canvas.itemconfig(canvas_window, width=event.width)

    canvas.bind("<Configure>", _on_canvas_configure)

    # Scroll con rueda del mouse
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    return outer, canvas, inner


def load_thumbnail(image_path: str, size=(160, 160)) -> ImageTk.PhotoImage | None:
    try:
        img = Image.open(image_path)
        img.thumbnail(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


def load_image(image_path: str, size=(300, 300)) -> ImageTk.PhotoImage | None:
    try:
        img = Image.open(image_path)
        img.thumbnail(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


class DropdownCheckbox(tk.Frame):
    """
    Botón desplegable con checkboxes para selección múltiple.
    """

    def __init__(self, parent, label: str, options: list, on_change=None, bg=None, **kwargs):
        bg = bg or S.BG
        super().__init__(parent, bg=bg, **kwargs)
        self.label = label
        self.options = options
        self.on_change = on_change
        self.vars: dict[str, tk.BooleanVar] = {}
        self._popup = None

        self.btn = tk.Button(
            self,
            text=f"{label} ▾",
            **S.BTN_SECONDARY,
            command=self._toggle,
        )
        self.btn.pack()

    def set_options(self, options: list):
        self.options = options
        self.vars = {}

    def _toggle(self):
        if self._popup and self._popup.winfo_exists():
            self._popup.destroy()
            self._popup = None
            return
        self._open_popup()

    def _open_popup(self):
        popup = tk.Toplevel(self)
        popup.overrideredirect(True)
        popup.configure(bg=S.BG_CARD)

        # Posición relativa al botón
        x = self.btn.winfo_rootx()
        y = self.btn.winfo_rooty() + self.btn.winfo_height()
        popup.geometry(f"+{x}+{y}")
        popup.lift()

        frame = tk.Frame(popup, bg=S.BG_CARD, relief="solid", bd=1)
        frame.pack(fill="both", expand=True, padx=1, pady=1)

        if not self.options:
            tk.Label(
                frame,
                text="Sin opciones",
                bg=S.BG_CARD,
                fg=S.TEXT_LIGHT,
                font=(S.FONT_FAMILY, S.FONT_SIZE_SM),
                padx=10,
                pady=6,
            ).pack()
        else:
            for opt in self.options:
                if opt not in self.vars:
                    self.vars[opt] = tk.BooleanVar(value=False)
                cb = tk.Checkbutton(
                    frame,
                    text=str(opt),
                    variable=self.vars[opt],
                    bg=S.BG_CARD,
                    fg=S.TEXT_DARK,
                    activebackground=S.BG_SIDEBAR,
                    font=(S.FONT_FAMILY, S.FONT_SIZE_MD),
                    anchor="w",
                    command=self._notify,
                )
                cb.pack(fill="x", padx=8, pady=2)

        def _close(event=None):
            popup.destroy()
            self._popup = None

        popup.bind("<FocusOut>", _close)
        popup.bind("<Escape>", _close)
        popup.focus_set()
        self._popup = popup

    def _notify(self):
        if self.on_change:
            self.on_change(self.get_selected())

    def get_selected(self) -> list:
        return [k for k, v in self.vars.items() if v.get()]

    def reset(self):
        for v in self.vars.values():
            v.set(False)


class Pagination(tk.Frame):
    """Barra de paginación simple."""

    def __init__(self, parent, on_page_change, bg=None, **kwargs):
        bg = bg or S.BG
        super().__init__(parent, bg=bg, **kwargs)
        self.on_page_change = on_page_change
        self.current_page = 1
        self.total_pages = 1

        self.btn_prev = tk.Button(
            self,
            text="← Anterior",
            **S.BTN_SECONDARY,
            command=self._prev,
        )
        self.btn_prev.pack(side="left", padx=4)

        self.lbl = tk.Label(
            self,
            text="Página 1 / 1",
            bg=bg,
            fg=S.TEXT_MEDIUM,
            font=(S.FONT_FAMILY, S.FONT_SIZE_MD),
        )
        self.lbl.pack(side="left", padx=8)

        self.btn_next = tk.Button(
            self,
            text="Siguiente →",
            **S.BTN_SECONDARY,
            command=self._next,
        )
        self.btn_next.pack(side="left", padx=4)

    def update(self, current: int, total: int):
        self.current_page = current
        self.total_pages = max(1, total)
        self.lbl.config(text=f"Página {self.current_page} / {self.total_pages}")
        self.btn_prev.config(state="normal" if current > 1 else "disabled")
        self.btn_next.config(state="normal" if current < total else "disabled")

    def _prev(self):
        if self.current_page > 1:
            self.on_page_change(self.current_page - 1)

    def _next(self):
        if self.current_page < self.total_pages:
            self.on_page_change(self.current_page + 1)
