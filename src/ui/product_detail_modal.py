"""
Modal de detalle de producto.

- Pills interactivos de Talla / Color que filtran el stock mostrado.
- show_actions=False  ->  solo boton Cerrar  (Inicio)
- show_actions=True   ->  Cerrar + Editar + Eliminar  (Productos)
"""
import tkinter as tk
from tkinter import messagebox
from collections import defaultdict
from src.models.producto import Producto
from src.services.producto_service import producto_service
from src.ui import widgets as W
from src.ui import styles as S


class ProductDetailModal(tk.Toplevel):
    def __init__(
        self,
        parent,
        product: Producto,
        on_save=None,
        show_actions: bool = False,
    ):
        super().__init__(parent)
        self.title("Detalle del Producto")
        self.configure(bg=S.BG)
        self.resizable(True, True)
        self.minsize(480, 400)
        self._photos = []
        self._product = product
        self._on_save = on_save
        self._show_actions = show_actions

        # Estado de seleccion de pills
        self._talla_sel: str | None = None
        self._color_sel: str | None = None

        # Mapas para filtrado rapido
        self._talla_colors: dict = defaultdict(set)   # {talla: {colores}}
        self._combo_stock:  dict = {}                  # {(talla, color): stock}
        for v in product.variantes:
            self._talla_colors[v.talla].add(v.color)
            self._combo_stock[(v.talla, v.color)] = v.stock

        self._pill_talla: dict[str, tk.Button] = {}
        self._pill_color: dict[str, tk.Button] = {}

        self._build(product)
        self._center()
        self.grab_set()

    def _center(self):
        self.update_idletasks()
        w = max(self.winfo_width(), 500)
        h = max(self.winfo_height(), 440)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w)//2}+{(sh - h)//2}")

    def _build(self, p: Producto):
        # Header
        header = tk.Frame(self, bg=S.PRIMARY, padx=20, pady=12)
        header.pack(fill="x")
        tk.Label(
            header, text=p.nombre,
            bg=S.PRIMARY, fg="white",
            font=(S.FONT_FAMILY, S.FONT_SIZE_TITLE, "bold"),
        ).pack(side="left")
        tk.Label(
            header, text=f"#{p.codigo}",
            bg=S.PRIMARY, fg=S.PRIMARY_LIGHT,
            font=(S.FONT_FAMILY, S.FONT_SIZE_MD),
        ).pack(side="right")

        outer, _, body = W.make_scrollable_frame(self, bg=S.BG)
        outer.pack(fill="both", expand=True, padx=20, pady=12)
        body.columnconfigure(1, weight=1)

        r = 0

        def _field(label, value, row):
            tk.Label(
                body, text=label + ":",
                bg=S.BG, fg=S.TEXT_MEDIUM,
                font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "bold"), anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=(0, 14), pady=2)
            tk.Label(
                body, text=value,
                bg=S.BG, fg=S.TEXT_DARK,
                font=(S.FONT_FAMILY, S.FONT_SIZE_MD),
                anchor="w", wraplength=340, justify="left",
            ).grid(row=row, column=1, sticky="w", pady=2)

        _field("Categoria",       p.categoria or "-",               r); r += 1
        _field("Descripcion",     p.descripcion or "-",             r); r += 1
        _field("Precio costo",    f"${p.precio_costo:.2f}",         r); r += 1
        _field("% Ganancia",      f"{p.porcentaje_ganancia:.1f}%",  r); r += 1
        _field("Precio unitario", f"${p.precio_unitario:.2f}",      r); r += 1

        # Imagenes
        if p.imagenes:
            tk.Label(
                body, text="Imagenes:",
                bg=S.BG, fg=S.TEXT_MEDIUM,
                font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "bold"), anchor="nw",
            ).grid(row=r, column=0, sticky="nw", padx=(0, 14), pady=(10, 4))
            strip = tk.Frame(body, bg=S.BG)
            strip.grid(row=r, column=1, sticky="w", pady=(10, 4))
            for img in p.imagenes:
                path = producto_service.get_image_path(img.filename)
                photo = W.load_thumbnail(path, size=(80, 80)) if path else None
                if photo:
                    self._photos.append(photo)
                    tk.Label(strip, image=photo, bg=S.BG, relief="solid", bd=1).pack(
                        side="left", padx=(0, 4)
                    )
            r += 1

        # Separador
        tk.Frame(body, bg=S.BORDER, height=1).grid(
            row=r, column=0, columnspan=2, sticky="ew", pady=(10, 8)
        )
        r += 1

        # ---- Variantes interactivas ----
        if p.variantes:
            tallas  = sorted(self._talla_colors.keys())
            colores = sorted({v.color for v in p.variantes})

            # Talles
            tk.Label(
                body, text="Talles:",
                bg=S.BG, fg=S.TEXT_MEDIUM,
                font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "bold"), anchor="nw",
            ).grid(row=r, column=0, sticky="nw", padx=(0, 14), pady=4)
            tallas_frame = tk.Frame(body, bg=S.BG)
            tallas_frame.grid(row=r, column=1, sticky="w", pady=4)
            for t in tallas:
                btn = self._make_pill(tallas_frame, t, self._toggle_talla)
                btn.pack(side="left", padx=(0, 6), pady=2)
                self._pill_talla[t] = btn
            r += 1

            # Colores
            tk.Label(
                body, text="Colores:",
                bg=S.BG, fg=S.TEXT_MEDIUM,
                font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "bold"), anchor="nw",
            ).grid(row=r, column=0, sticky="nw", padx=(0, 14), pady=4)
            colores_frame = tk.Frame(body, bg=S.BG)
            colores_frame.grid(row=r, column=1, sticky="w", pady=4)
            for c in colores:
                btn = self._make_pill(colores_frame, c, self._toggle_color)
                btn.pack(side="left", padx=(0, 6), pady=2)
                self._pill_color[c] = btn
            r += 1

            # Stock
            tk.Label(
                body, text="Stock:",
                bg=S.BG, fg=S.TEXT_MEDIUM,
                font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "bold"), anchor="w",
            ).grid(row=r, column=0, sticky="w", padx=(0, 14), pady=4)
            stock_row = tk.Frame(body, bg=S.BG)
            stock_row.grid(row=r, column=1, sticky="w", pady=4)
            self._stock_var = tk.StringVar(value=str(p.stock_total))
            tk.Label(
                stock_row, textvariable=self._stock_var,
                bg=S.BG, fg=S.PRIMARY_DARK,
                font=(S.FONT_FAMILY, S.FONT_SIZE_LG, "bold"), anchor="w",
            ).pack(side="left")
            self._stock_hint = tk.Label(
                stock_row, text="(total)",
                bg=S.BG, fg=S.TEXT_LIGHT,
                font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "italic"), anchor="w",
            )
            self._stock_hint.pack(side="left", padx=(6, 0))
        else:
            tk.Label(
                body, text="Sin variantes registradas.",
                bg=S.BG, fg=S.TEXT_LIGHT,
                font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "italic"),
            ).grid(row=r, column=0, columnspan=2, sticky="w", pady=4)

        # Footer
        btn_frame = tk.Frame(self, bg=S.BG)
        btn_frame.pack(fill="x", padx=16, pady=(4, 16))
        tk.Button(
            btn_frame, text="Cerrar",
            **S.BTN_SECONDARY, command=self.destroy,
        ).pack(side="right")
        if self._show_actions:
            tk.Button(
                btn_frame, text="\u270f Editar",
                **S.BTN_SUCCESS, command=self._on_edit,
            ).pack(side="right", padx=(0, 8))
            tk.Button(
                btn_frame, text="\U0001f5d1 Eliminar",
                **S.BTN_DANGER, command=self._on_delete,
            ).pack(side="left")

    # ------------------------------------------------------------------
    # Pills
    # ------------------------------------------------------------------

    def _make_pill(self, parent: tk.Frame, text: str, command) -> tk.Button:
        return tk.Button(
            parent, text=text,
            bg=S.BG_SIDEBAR, fg=S.TEXT_DARK,
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM),
            relief="flat", bd=0, padx=10, pady=4,
            cursor="hand2",
            command=lambda t=text: command(t),
        )

    def _toggle_talla(self, talla: str):
        if self._talla_sel == talla:
            self._talla_sel = None
        else:
            self._talla_sel = talla
            # Deseleccionar color si no pertenece a esta talla
            if self._color_sel and self._color_sel not in self._talla_colors.get(talla, set()):
                self._color_sel = None
        self._refresh_pills()

    def _toggle_color(self, color: str):
        if color not in self._available_colors():
            return
        self._color_sel = None if self._color_sel == color else color
        self._refresh_pills()

    def _available_colors(self) -> set:
        if self._talla_sel:
            return self._talla_colors.get(self._talla_sel, set())
        return {v.color for v in self._product.variantes}

    def _refresh_pills(self):
        avail = self._available_colors()

        for t, btn in self._pill_talla.items():
            if t == self._talla_sel:
                btn.config(bg=S.PRIMARY, fg="white")
            else:
                btn.config(bg=S.BG_SIDEBAR, fg=S.TEXT_DARK)

        for c, btn in self._pill_color.items():
            if c not in avail:
                btn.config(bg="#EEEEEE", fg=S.TEXT_LIGHT, cursor="arrow")
            elif c == self._color_sel:
                btn.config(bg=S.PRIMARY, fg="white", cursor="hand2")
            else:
                btn.config(bg=S.BG_SIDEBAR, fg=S.TEXT_DARK, cursor="hand2")

        self._update_stock()

    def _update_stock(self):
        p = self._product
        if self._talla_sel and self._color_sel:
            stock = self._combo_stock.get((self._talla_sel, self._color_sel), 0)
            hint  = f"(talle {self._talla_sel} / {self._color_sel})"
        elif self._talla_sel:
            stock = sum(v.stock for v in p.variantes if v.talla == self._talla_sel)
            hint  = f"(talle {self._talla_sel}, todos los colores)"
        elif self._color_sel:
            stock = sum(v.stock for v in p.variantes if v.color == self._color_sel)
            hint  = f"({self._color_sel}, todos los talles)"
        else:
            stock = p.stock_total
            hint  = "(total)"
        self._stock_var.set(str(stock))
        self._stock_hint.config(text=hint)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_edit(self):
        from src.ui.product_form_modal import ProductFormModal

        def _saved():
            if self._on_save:
                self._on_save()
            self.destroy()

        ProductFormModal(self, product=self._product, on_save=_saved)

    def _on_delete(self):
        p = self._product
        if messagebox.askyesno(
            "Confirmar eliminacion",
            f"Eliminar '{p.nombre}' (#{p.codigo})?\nEsta accion no se puede deshacer.",
            parent=self,
        ):
            producto_service.eliminar(p.id)
            if self._on_save:
                self._on_save()
            self.destroy()
