"""
Sección Productos: listado paginado, buscador, nuevo/editar/eliminar producto.
Vistas: tabla y cuadrícula (cards). Consume ProductoService — no conoce SQL.
"""
import tkinter as tk
from tkinter import ttk, messagebox

from src.models.producto import Producto
from src.services.producto_service import producto_service
from src.ui import widgets as W
from src.ui import styles as S
from src.ui.product_form_modal import ProductFormModal


PAGE_SIZE = 15


class ProductsSection(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=S.BG, **kwargs)
        self._current_page = 1
        self._total_pages  = 1
        self._search_query = ""
        self._view_mode    = "table"        # "table" | "grid"
        self._products: list[Producto] = []
        self._grid_photos: list = []
        self._build()
        self.refresh()

    # ── Construcción de la UI ─────────────────────────────────────────────

    def _build(self):
        # Cabecera
        header = tk.Frame(self, bg=S.BG, padx=16, pady=12)
        header.pack(fill="x")
        tk.Label(header, text="Productos", **S.LABEL_TITLE, padx=0).pack(side="left")

        # Botones de toggle de vista
        toggle = tk.Frame(header, bg=S.BG)
        toggle.pack(side="right", padx=(8, 0))
        self.btn_grid_view = tk.Button(
            toggle, text="⊞ Cuadrícula",
            bg=S.BG_SIDEBAR, fg=S.PRIMARY_DARK,
            font=(S.FONT_FAMILY, S.FONT_SIZE_MD),
            relief="flat", bd=0, padx=10, pady=5, cursor="hand2",
            command=lambda: self._set_view("grid"),
        )
        self.btn_grid_view.pack(side="left", padx=(0, 4))
        self.btn_table_view = tk.Button(
            toggle, text="☰ Tabla",
            bg=S.PRIMARY, fg="white",
            font=(S.FONT_FAMILY, S.FONT_SIZE_MD),
            relief="flat", bd=0, padx=10, pady=5, cursor="hand2",
            command=lambda: self._set_view("table"),
        )
        self.btn_table_view.pack(side="left", padx=(0, 8))

        tk.Button(
            header, text="+ Nuevo Producto",
            **S.BTN_PRIMARY, command=self._open_new_form,
        ).pack(side="right")

        # Buscador
        search_bar = tk.Frame(self, bg=S.BG, padx=16, pady=8)
        search_bar.pack(fill="x")
        tk.Label(
            search_bar, text="🔍",
            bg=S.BG, fg=S.TEXT_MEDIUM, font=(S.FONT_FAMILY, 13),
        ).pack(side="left", padx=(0, 6))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._on_search())
        tk.Entry(
            search_bar, textvariable=self.search_var,
            font=(S.FONT_FAMILY, S.FONT_SIZE_MD),
            bg="white", fg=S.TEXT_DARK,
            relief="solid", bd=1, width=50,
        ).pack(side="left", fill="x", expand=True, ipady=5)
        tk.Button(
            search_bar, text="Buscar",
            **S.BTN_PRIMARY, command=self._on_search,
        ).pack(side="left", padx=(8, 0))
        tk.Button(
            search_bar, text="Limpiar",
            **S.BTN_SECONDARY, command=self._clear_search,
        ).pack(side="left", padx=(4, 0))

        # Contador
        self.lbl_count = tk.Label(
            self, text="",
            bg=S.BG, fg=S.TEXT_MEDIUM,
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM),
        )
        self.lbl_count.pack(anchor="w", padx=16)

        # Contenedor tabla (se muestra u oculta según la vista)
        self.table_container = tk.Frame(self, bg=S.BG)
        self._build_table()

        # Contenedor cuadrícula (se muestra u oculta según la vista)
        self.grid_outer, _, self.grid_frame = W.make_scrollable_frame(self, bg=S.BG)

        # Paginación (siempre visible)
        self.pagination = W.Pagination(self, on_page_change=self._go_to_page, bg=S.BG)
        self.pagination.pack(pady=(6, 14))

        # Vista inicial: tabla
        self._apply_view()

    def _apply_view(self):
        if self._view_mode == "table":
            self.grid_outer.pack_forget()
            self.table_container.pack(fill="both", expand=True, padx=16)
            self.btn_table_view.config(bg=S.PRIMARY, fg="white")
            self.btn_grid_view.config(bg=S.BG_SIDEBAR, fg=S.PRIMARY_DARK)
        else:
            self.table_container.pack_forget()
            self.grid_outer.pack(fill="both", expand=True, padx=16, pady=(4, 0))
            self.btn_grid_view.config(bg=S.PRIMARY, fg="white")
            self.btn_table_view.config(bg=S.BG_SIDEBAR, fg=S.PRIMARY_DARK)

    def _set_view(self, mode: str):
        if self._view_mode == mode:
            return
        self._view_mode = mode
        self._apply_view()
        self._render_current_view()

    def _build_table(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Products.Treeview",
            background=S.BG_CARD, foreground=S.TEXT_DARK,
            fieldbackground=S.BG_CARD, rowheight=30,
            font=(S.FONT_FAMILY, S.FONT_SIZE_MD),
        )
        style.configure(
            "Products.Treeview.Heading",
            background=S.PRIMARY, foreground="white",
            font=(S.FONT_FAMILY, S.FONT_SIZE_MD, "bold"), relief="flat",
        )
        style.map("Products.Treeview", background=[("selected", S.PRIMARY_LIGHT)])

        columns = ("codigo", "nombre", "categoria", "variantes", "stock", "precio_unitario", "nota")
        vsb = ttk.Scrollbar(self.table_container, orient="vertical")
        hsb = ttk.Scrollbar(self.table_container, orient="horizontal")

        self.tree = ttk.Treeview(
            self.table_container, columns=columns, show="headings",
            style="Products.Treeview",
            yscrollcommand=vsb.set, xscrollcommand=hsb.set,
            selectmode="browse",
        )
        vsb.configure(command=self.tree.yview)
        hsb.configure(command=self.tree.xview)

        for col, (heading, width) in zip(columns, [
            ("Código", 90), ("Nombre", 200), ("Categoría", 110),
            ("Variantes", 100), ("Stock", 70),
            ("P. Unitario", 100), ("", 80),
        ]):
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=width, anchor="w", minwidth=50)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.table_container.rowconfigure(0, weight=1)
        self.table_container.columnconfigure(0, weight=1)

        # Panel de acciones (dentro de table_container)
        action_frame = tk.Frame(self.table_container, bg=S.BG)
        action_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 0))

        self.lbl_selected = tk.Label(
            action_frame,
            text="Selecciona un producto para editarlo o eliminarlo.",
            bg=S.BG, fg=S.TEXT_LIGHT,
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "italic"),
        )
        self.lbl_selected.pack(side="left")

        self.btn_edit = tk.Button(
            action_frame, text="✏ Editar",
            **S.BTN_SUCCESS, command=self._edit_selected, state="disabled",
        )
        self.btn_edit.pack(side="right", padx=(6, 0))

        self.btn_delete = tk.Button(
            action_frame, text="🗑 Eliminar",
            **S.BTN_DANGER, command=self._delete_selected, state="disabled",
        )
        self.btn_delete.pack(side="right")

        self.tree.bind("<<TreeviewSelect>>", self._on_row_select)

        def _on_row_double_click(event):
            item = self.tree.identify_row(event.y)
            if item:
                from src.ui.product_detail_modal import ProductDetailModal as _PDM
                prod = producto_service.obtener_por_id(int(item))
                if prod:
                    _PDM(self, prod, on_save=self.refresh, show_actions=True)

        self.tree.bind("<Double-1>", _on_row_double_click)

    # ── Datos ─────────────────────────────────────────────────────────────

    def _on_search(self, *_):
        self._search_query = self.search_var.get().strip()
        self._current_page = 1
        self._load_page()

    def _clear_search(self):
        self.search_var.set("")
        self._search_query = ""
        self._current_page = 1
        self._load_page()

    def _go_to_page(self, page: int):
        self._current_page = page
        self._load_page()

    def _load_page(self):
        products, total = producto_service.listar_paginado(
            search=self._search_query,
            page=self._current_page,
            page_size=PAGE_SIZE,
        )
        self._products = products
        self._total_pages = producto_service.calcular_total_paginas(total, PAGE_SIZE)
        self.pagination.update(self._current_page, self._total_pages)
        self.lbl_count.config(text=f"{total} producto(s) en total")
        self._render_current_view()
        self._deselect()

    def _render_current_view(self):
        if self._view_mode == "table":
            self._populate_tree(self._products)
        else:
            self._render_grid()

    def _populate_tree(self, products: list[Producto]):
        self.tree.delete(*self.tree.get_children())
        for p in products:
            variantes_txt = f"{len(p.variantes)} variante(s)" if p.variantes else "-"
            self.tree.insert("", "end", iid=str(p.id), values=(
                p.codigo, p.nombre, p.categoria, variantes_txt,
                p.stock_total, S.fmt_moneda(p.precio_unitario), "",
            ))

    def refresh(self):
        self._current_page = 1
        self._load_page()

    # ── Vista cuadrícula ──────────────────────────────────────────────────

    def _render_grid(self):
        for w in self.grid_frame.winfo_children():
            w.destroy()
        self._grid_photos.clear()

        if not self._products:
            tk.Label(
                self.grid_frame,
                text="No se encontraron productos.",
                bg=S.BG, fg=S.TEXT_LIGHT,
                font=(S.FONT_FAMILY, S.FONT_SIZE_LG),
            ).pack(pady=40)
            return

        self.grid_frame.columnconfigure(tuple(range(4)), weight=1, uniform="card")
        for idx, p in enumerate(self._products):
            row, col = divmod(idx, 4)
            self._make_card(self.grid_frame, p).grid(
                row=row, column=col, padx=8, pady=8, sticky="nsew",
            )

    def _make_card(self, parent, p: Producto) -> tk.Frame:
        from src.ui.product_detail_modal import ProductDetailModal
        card = tk.Frame(parent, bg=S.BG_CARD, relief="solid", bd=1, cursor="hand2")
        card.configure(highlightbackground=S.BORDER, highlightthickness=1)

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
            info, text=S.fmt_moneda(p.precio_unitario),
            bg=S.BG_CARD, fg=S.PRIMARY,
            font=(S.FONT_FAMILY, S.FONT_SIZE_LG, "bold"), anchor="w",
        ).pack(anchor="w", pady=(4, 0))

        def _enter(e, c=card):  c.configure(highlightbackground=S.PRIMARY)
        def _leave(e, c=card):  c.configure(highlightbackground=S.BORDER)
        def _click(e, prod=p):  ProductDetailModal(self, prod, on_save=self.refresh, show_actions=True)

        for widget in [card, img_lbl, info] + list(info.winfo_children()):
            widget.bind("<Enter>",    _enter)
            widget.bind("<Leave>",    _leave)
            widget.bind("<Button-1>", _click)

        return card

    # ── Selección y acciones ──────────────────────────────────────────────

    def _on_row_select(self, event=None):
        selected = self.tree.selection()
        if selected:
            p = producto_service.obtener_por_id(int(selected[0]))
            if p:
                self.lbl_selected.config(
                    text=f"Seleccionado: {p.nombre}  (#{p.codigo})",
                    fg=S.TEXT_DARK,
                )
                self.btn_edit.config(state="normal")
                self.btn_delete.config(state="normal")

    def _deselect(self):
        self.tree.selection_remove(self.tree.selection())
        self.lbl_selected.config(
            text="Selecciona un producto para editarlo o eliminarlo.",
            fg=S.TEXT_LIGHT,
        )
        self.btn_edit.config(state="disabled")
        self.btn_delete.config(state="disabled")

    def _get_selected_product(self) -> Producto | None:
        selected = self.tree.selection()
        if not selected:
            return None
        return producto_service.obtener_por_id(int(selected[0]))

    def _open_new_form(self):
        ProductFormModal(self, product=None, on_save=self.refresh)

    def _edit_selected(self):
        p = self._get_selected_product()
        if p:
            ProductFormModal(self, product=p, on_save=self.refresh)

    def _delete_selected(self):
        p = self._get_selected_product()
        if not p:
            return
        confirm = messagebox.askyesno(
            "Confirmar eliminación",
            f"¿Eliminar '{p.nombre}' (#{p.codigo})?\nEsta acción no se puede deshacer.",
            parent=self,
        )
        if confirm:
            producto_service.eliminar(p.id)
            self.refresh()
