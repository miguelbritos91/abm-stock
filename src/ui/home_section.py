"""
Sección Inicio: buscador, filtros desplegables, vistas tabla y cuadrícula.
Consume ProductoService — no conoce SQL ni rutas de archivo.
"""
import tkinter as tk
from tkinter import ttk

from src.models.producto import Producto
from src.services.producto_service import producto_service
from src.ui import widgets as W
from src.ui import styles as S
from src.ui.product_detail_modal import ProductDetailModal


class HomeSection(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=S.BG, **kwargs)
        self._view_mode = "grid"        # "grid" | "table"
        self._products: list[Producto] = []
        self._grid_photos: list = []    # referencias para evitar GC de PhotoImage

        self._build_toolbar()
        self._build_filters()
        self._build_results_area()
        self.refresh()

    # ── Toolbar ──────────────────────────────────────────────────────────

    def _build_toolbar(self):
        bar = tk.Frame(self, bg=S.BG, pady=12, padx=16)
        bar.pack(fill="x")

        tk.Label(bar, text="Inicio", **S.LABEL_TITLE, padx=0).pack(side="left")

        toggle = tk.Frame(bar, bg=S.BG)
        toggle.pack(side="right", padx=(0, 4))

        self.btn_grid_view = tk.Button(
            toggle, text="⊞ Cuadrícula",
            bg=S.PRIMARY, fg="white",
            font=(S.FONT_FAMILY, S.FONT_SIZE_MD),
            relief="flat", bd=0, padx=10, pady=5, cursor="hand2",
            command=lambda: self._set_view("grid"),
        )
        self.btn_grid_view.pack(side="left", padx=(0, 4))

        self.btn_table_view = tk.Button(
            toggle, text="☰ Tabla",
            bg=S.BG_SIDEBAR, fg=S.PRIMARY_DARK,
            font=(S.FONT_FAMILY, S.FONT_SIZE_MD),
            relief="flat", bd=0, padx=10, pady=5, cursor="hand2",
            command=lambda: self._set_view("table"),
        )
        self.btn_table_view.pack(side="left")

    # ── Filtros ───────────────────────────────────────────────────────────

    def _build_filters(self):
        area = tk.Frame(self, bg=S.BG, pady=6, padx=16)
        area.pack(fill="x")

        # Buscador
        search_frame = tk.Frame(area, bg=S.BG)
        search_frame.pack(fill="x", pady=(0, 8))

        tk.Label(
            search_frame, text="🔍",
            bg=S.BG, fg=S.TEXT_MEDIUM, font=(S.FONT_FAMILY, 13),
        ).pack(side="left", padx=(0, 6))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._on_filter_change())
        tk.Entry(
            search_frame,
            textvariable=self.search_var,
            font=(S.FONT_FAMILY, S.FONT_SIZE_MD),
            bg="white", fg=S.TEXT_DARK,
            relief="solid", bd=1, width=45,
        ).pack(side="left", fill="x", expand=True, ipady=5)
        tk.Button(
            search_frame, text="Buscar",
            **S.BTN_PRIMARY, command=self._on_filter_change,
        ).pack(side="left", padx=(8, 0))

        # Fila de dropdowns
        filters_row = tk.Frame(area, bg=S.BG)
        filters_row.pack(fill="x", pady=(0, 4))

        tk.Label(
            filters_row, text="Filtros:",
            bg=S.BG, fg=S.TEXT_MEDIUM,
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "bold"),
        ).pack(side="left", padx=(0, 8))

        self.dd_categoria = W.DropdownCheckbox(
            filters_row, "Categoría", [],
            on_change=lambda _: self._on_filter_change(), bg=S.BG,
        )
        self.dd_categoria.pack(side="left", padx=(0, 6))

        self.dd_talla = W.DropdownCheckbox(
            filters_row, "Talla", [],
            on_change=lambda _: self._on_filter_change(), bg=S.BG,
        )
        self.dd_talla.pack(side="left", padx=(0, 6))

        self.dd_color = W.DropdownCheckbox(
            filters_row, "Color", [],
            on_change=lambda _: self._on_filter_change(), bg=S.BG,
        )
        self.dd_color.pack(side="left", padx=(0, 6))

        self.dd_orden = W.DropdownCheckbox(
            filters_row, "Ordenar precio",
            ["Menor a mayor", "Mayor a menor"],
            on_change=self._on_order_change, bg=S.BG,
        )
        self.dd_orden.pack(side="left", padx=(0, 6))

        tk.Button(
            filters_row, text="Limpiar filtros",
            **S.BTN_SECONDARY, command=self._clear_filters,
        ).pack(side="left", padx=(8, 0))

        self.lbl_count = tk.Label(
            area, text="",
            bg=S.BG, fg=S.TEXT_MEDIUM,
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM),
        )
        self.lbl_count.pack(anchor="w", pady=(4, 0))

    def _build_results_area(self):
        self.results_outer, self.results_canvas, self.results_frame = (
            W.make_scrollable_frame(self, bg=S.BG)
        )
        self.results_outer.pack(fill="both", expand=True, padx=16, pady=(4, 16))

    # ── Lógica de filtros ─────────────────────────────────────────────────

    def _on_order_change(self, selected: list):
        # Solo un orden activo a la vez
        if len(selected) > 1:
            last = selected[-1]
            for k, v in self.dd_orden.vars.items():
                v.set(k == last)
        self._on_filter_change()

    def _on_filter_change(self, *_):
        search     = self.search_var.get().strip()
        categorias = self.dd_categoria.get_selected() or None
        tallas     = self.dd_talla.get_selected()     or None
        colores    = self.dd_color.get_selected()     or None

        orden_sel = self.dd_orden.get_selected()
        if "Mayor a menor" in orden_sel:
            orden = "precio_desc"
        elif "Menor a mayor" in orden_sel:
            orden = "precio_asc"
        else:
            orden = "nombre"

        self._products = producto_service.filtrar(
            search=search,
            categorias=categorias,
            tallas=tallas,
            colores=colores,
            orden=orden,
        )
        self.lbl_count.config(text=f"{len(self._products)} producto(s) encontrado(s)")
        self._render_results()

    def _clear_filters(self):
        self.search_var.set("")
        self.dd_categoria.reset()
        self.dd_talla.reset()
        self.dd_color.reset()
        self.dd_orden.reset()
        self._on_filter_change()

    def _set_view(self, mode: str):
        self._view_mode = mode
        if mode == "grid":
            self.btn_grid_view.config(bg=S.PRIMARY, fg="white")
            self.btn_table_view.config(bg=S.BG_SIDEBAR, fg=S.PRIMARY_DARK)
        else:
            self.btn_table_view.config(bg=S.PRIMARY, fg="white")
            self.btn_grid_view.config(bg=S.BG_SIDEBAR, fg=S.PRIMARY_DARK)
        self._render_results()

    def refresh(self):
        """Recarga opciones de filtro y resultados (se llama al cambiar de sección)."""
        opciones = producto_service.obtener_opciones_filtro()
        self.dd_categoria.set_options(opciones["categorias"])
        self.dd_talla.set_options(opciones["tallas"])
        self.dd_color.set_options(opciones["colores"])
        self._on_filter_change()

    # ── Render ────────────────────────────────────────────────────────────

    def _clear_results(self):
        for w in self.results_frame.winfo_children():
            w.destroy()
        self._grid_photos.clear()

    def _render_results(self):
        self._clear_results()
        if not self._products:
            tk.Label(
                self.results_frame,
                text="No se encontraron productos.",
                bg=S.BG, fg=S.TEXT_LIGHT,
                font=(S.FONT_FAMILY, S.FONT_SIZE_LG),
            ).pack(pady=40)
            return
        if self._view_mode == "grid":
            self._render_grid()
        else:
            self._render_table()

    # ── Vista cuadrícula ──────────────────────────────────────────────────

    def _render_grid(self):
        container = self.results_frame
        container.columnconfigure(tuple(range(4)), weight=1, uniform="card")
        for idx, p in enumerate(self._products):
            row, col = divmod(idx, 4)
            self._make_card(container, p).grid(
                row=row, column=col, padx=8, pady=8, sticky="nsew"
            )

    def _make_card(self, parent, p: Producto) -> tk.Frame:
        card = tk.Frame(
            parent, bg=S.BG_CARD, relief="solid", bd=1, cursor="hand2",
        )
        card.configure(highlightbackground=S.BORDER, highlightthickness=1)

        # Imagen
        img_path = producto_service.get_image_path(p.imagen_principal)
        photo = W.load_thumbnail(img_path, size=(160, 160)) if img_path else None
        if photo:
            self._grid_photos.append(photo)
            img_lbl = tk.Label(card, image=photo, bg=S.BG_CARD, cursor="hand2")
        else:
            img_lbl = tk.Label(
                card, text="📷", bg=S.BG_SIDEBAR,
                fg=S.TEXT_LIGHT, font=(S.FONT_FAMILY, 28),
                width=14, height=6, cursor="hand2",
            )
        img_lbl.pack(fill="x")

        info = tk.Frame(card, bg=S.BG_CARD, padx=8, pady=6)
        info.pack(fill="x")

        tk.Label(
            info, text=p.nombre,
            bg=S.BG_CARD, fg=S.TEXT_DARK,
            font=(S.FONT_FAMILY, S.FONT_SIZE_MD, "bold"),
            anchor="w", wraplength=150, justify="left",
        ).pack(anchor="w")
        variantes_txt = f"{len(p.variantes)} variante(s)" if p.variantes else "Sin variantes"
        tk.Label(
            info, text=variantes_txt,
            bg=S.BG_CARD, fg=S.TEXT_MEDIUM,
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM), anchor="w",
        ).pack(anchor="w")
        tk.Label(
            info, text=f"${p.precio_unitario:.2f}",
            bg=S.BG_CARD, fg=S.PRIMARY,
            font=(S.FONT_FAMILY, S.FONT_SIZE_LG, "bold"), anchor="w",
        ).pack(anchor="w", pady=(4, 0))

        # Hover y click
        def _enter(e, c=card):   c.configure(highlightbackground=S.PRIMARY)
        def _leave(e, c=card):   c.configure(highlightbackground=S.BORDER)
        def _click(e, prod=p):   ProductDetailModal(self, prod)

        for widget in [card, img_lbl, info] + list(info.winfo_children()):
            widget.bind("<Enter>",    _enter)
            widget.bind("<Leave>",    _leave)
            widget.bind("<Button-1>", _click)

        return card

    # ── Vista tabla ───────────────────────────────────────────────────────

    def _render_table(self):
        columns = ("codigo", "nombre", "categoria", "variantes",
                   "stock", "precio_costo", "precio_unitario")
        headers = ("Código", "Nombre", "Categoría", "Variantes",
                   "Stock total", "Costo", "P. Unitario")
        widths  = (90, 180, 110, 100, 80, 90, 100)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Home.Treeview",
            background=S.BG_CARD, foreground=S.TEXT_DARK,
            fieldbackground=S.BG_CARD, rowheight=28,
            font=(S.FONT_FAMILY, S.FONT_SIZE_MD),
        )
        style.configure(
            "Home.Treeview.Heading",
            background=S.PRIMARY, foreground="white",
            font=(S.FONT_FAMILY, S.FONT_SIZE_MD, "bold"), relief="flat",
        )
        style.map("Home.Treeview", background=[("selected", S.PRIMARY_LIGHT)])

        tree_frame = tk.Frame(self.results_frame, bg=S.BG)
        tree_frame.pack(fill="both", expand=True)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings",
            style="Home.Treeview",
            yscrollcommand=vsb.set, xscrollcommand=hsb.set,
        )
        vsb.configure(command=tree.yview)
        hsb.configure(command=tree.xview)

        for col, header, width in zip(columns, headers, widths):
            tree.heading(col, text=header)
            tree.column(col, width=width, anchor="w", minwidth=50)

        for p in self._products:
            variantes_txt = f"{len(p.variantes)} variante(s)" if p.variantes else "-"
            tree.insert("", "end", iid=str(p.id), values=(
                p.codigo, p.nombre, p.categoria, variantes_txt,
                p.stock_total, f"${p.precio_costo:.2f}", f"${p.precio_unitario:.2f}",
            ))

        def _on_double_click(event):
            item = tree.identify_row(event.y)
            if item:
                prod = next((p for p in self._products if str(p.id) == item), None)
                if prod:
                    ProductDetailModal(self, prod)

        tree.bind("<Double-1>", _on_double_click)

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        tk.Label(
            self.results_frame,
            text="Doble clic en una fila para ver detalle",
            bg=S.BG, fg=S.TEXT_LIGHT,
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "italic"),
        ).pack(anchor="e", pady=(2, 0))
