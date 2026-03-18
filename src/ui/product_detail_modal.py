"""
Modal de detalle de producto.

- Pills interactivos de Talla / Color que filtran el stock mostrado.
- Carrusel de imágenes: tira con scroll horizontal + lightbox al hacer clic.
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
        self._combo_id:     dict = {}                  # {(talla, color): variante_id}
        for v in product.variantes:
            self._talla_colors[v.talla].add(v.color)
            self._combo_stock[(v.talla, v.color)] = v.stock
            self._combo_id[(v.talla, v.color)]    = v.id

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
        _field("Precio costo",      S.fmt_moneda(p.precio_costo),        r); r += 1
        _field("% Ganancia",        f"{p.porcentaje_ganancia:.1f}%", r); r += 1
        _field("Precio sugerido",   S.fmt_moneda(p.precio_sugerido),    r); r += 1
        _field("Precio unitario",   S.fmt_moneda(p.precio_unitario),    r); r += 1

        # Imagenes — tira horizontal con scroll y lightbox al clicar
        if p.imagenes:
            tk.Label(
                body, text="Imagenes:",
                bg=S.BG, fg=S.TEXT_MEDIUM,
                font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "bold"), anchor="nw",
            ).grid(row=r, column=0, sticky="nw", padx=(0, 14), pady=(10, 4))

            # Contenedor de la tira con scroll horizontal
            strip_outer = tk.Frame(body, bg=S.BG)
            strip_outer.grid(row=r, column=1, sticky="w", pady=(10, 4))

            strip_canvas = tk.Canvas(
                strip_outer, bg=S.BG, height=96, highlightthickness=0,
            )
            h_scroll = tk.Scrollbar(
                strip_outer, orient="horizontal", command=strip_canvas.xview,
            )
            strip_canvas.configure(xscrollcommand=h_scroll.set)
            strip_canvas.pack(side="top", fill="x")
            h_scroll.pack(side="top", fill="x")

            inner_strip = tk.Frame(strip_canvas, bg=S.BG)
            strip_canvas.create_window((0, 0), window=inner_strip, anchor="nw")
            inner_strip.bind(
                "<Configure>",
                lambda e: strip_canvas.configure(
                    scrollregion=strip_canvas.bbox("all"),
                    width=min(e.width, 500),
                ),
            )

            # Scroll horizontal con rueda del mouse sobre la tira
            strip_canvas.bind(
                "<MouseWheel>",
                lambda e: strip_canvas.xview_scroll(int(-1 * (e.delta / 120)), "units"),
            )

            # Cargar miniaturas y construir índice de paths
            self._img_paths: list[str] = []
            for img in p.imagenes:
                path = producto_service.get_image_path(img.filename)
                if not path:
                    continue
                photo = W.load_thumbnail(path, size=(80, 80))
                if not photo:
                    continue
                self._photos.append(photo)
                self._img_paths.append(path)
                idx = len(self._img_paths) - 1
                lbl = tk.Label(
                    inner_strip, image=photo, bg=S.BG,
                    relief="solid", bd=1, cursor="hand2",
                )
                lbl.pack(side="left", padx=(0, 5))
                lbl.bind("<Button-1>", lambda e, i=idx: self._open_lightbox(i))
                # Tooltip de índice
                lbl.bind("<Enter>", lambda e, i=idx: e.widget.config(relief="sunken", bd=2))
                lbl.bind("<Leave>", lambda e: e.widget.config(relief="solid", bd=1))

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
        else:
            # Botón "Agregar a venta" solo visible desde Inicio
            self._btn_add_venta = tk.Button(
                btn_frame, text="\U0001f6d2 Agregar a venta",
                **S.BTN_PRIMARY, command=self._on_agregar_venta,
                state="disabled",
            )
            self._btn_add_venta.pack(side="left")

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
        # Habilitar/deshabilitar botón de agregar a venta
        if not self._show_actions and hasattr(self, "_btn_add_venta"):
            key = (self._talla_sel, self._color_sel)
            combo_stock = self._combo_stock.get(key, 0)
            can_add = (self._talla_sel is not None and
                       self._color_sel is not None and
                       self._combo_id.get(key) is not None and
                       combo_stock > 0)
            self._btn_add_venta.config(state="normal" if can_add else "disabled")

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

    # ------------------------------------------------------------------
    # Lightbox — carrusel de imágenes ampliadas
    # ------------------------------------------------------------------

    def _open_lightbox(self, start_index: int = 0):
        paths = getattr(self, "_img_paths", [])
        if not paths:
            return

        lb = tk.Toplevel(self)
        lb.title("Imágenes del producto")
        lb.configure(bg="#1A1A1A")
        lb.resizable(True, True)
        lb.minsize(600, 500)
        lb.grab_set()

        state = {"idx": start_index, "main_photo": None, "thumb_photos": []}

        # ── Área de imagen principal ──────────────────────────────────────
        top_frame = tk.Frame(lb, bg="#1A1A1A")
        top_frame.pack(fill="both", expand=True, padx=12, pady=(12, 6))

        btn_prev = tk.Button(
            top_frame, text="❮",
            bg="#2C2C2C", fg="white",
            font=(S.FONT_FAMILY, 18, "bold"),
            relief="flat", cursor="hand2", bd=0,
            activebackground="#444", activeforeground="white",
            padx=10,
        )
        btn_prev.pack(side="left", fill="y")

        img_canvas = tk.Canvas(top_frame, bg="#1A1A1A", highlightthickness=0)
        img_canvas.pack(side="left", fill="both", expand=True)

        btn_next = tk.Button(
            top_frame, text="❯",
            bg="#2C2C2C", fg="white",
            font=(S.FONT_FAMILY, 18, "bold"),
            relief="flat", cursor="hand2", bd=0,
            activebackground="#444", activeforeground="white",
            padx=10,
        )
        btn_next.pack(side="left", fill="y")

        counter_var = tk.StringVar()
        tk.Label(
            lb, textvariable=counter_var,
            bg="#1A1A1A", fg="#AAAAAA",
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM),
        ).pack(pady=(0, 4))

        # ── Tira de miniaturas inferior ───────────────────────────────────
        thumb_outer = tk.Frame(lb, bg="#1A1A1A")
        thumb_outer.pack(fill="x", padx=12, pady=(0, 12))

        thumb_canvas = tk.Canvas(
            thumb_outer, bg="#1A1A1A", height=74, highlightthickness=0,
        )
        thumb_scroll = tk.Scrollbar(
            thumb_outer, orient="horizontal", command=thumb_canvas.xview,
        )
        thumb_canvas.configure(xscrollcommand=thumb_scroll.set)
        thumb_canvas.pack(side="top", fill="x")
        thumb_scroll.pack(side="top", fill="x")

        thumb_strip = tk.Frame(thumb_canvas, bg="#1A1A1A")
        thumb_canvas.create_window((0, 0), window=thumb_strip, anchor="nw")
        thumb_strip.bind(
            "<Configure>",
            lambda e: thumb_canvas.configure(scrollregion=thumb_canvas.bbox("all")),
        )
        thumb_canvas.bind(
            "<MouseWheel>",
            lambda e: thumb_canvas.xview_scroll(int(-1 * (e.delta / 120)), "units"),
        )

        thumb_labels: list[tk.Label] = []
        for i, path in enumerate(paths):
            ph = W.load_thumbnail(path, size=(60, 60))
            state["thumb_photos"].append(ph)
            lbl = tk.Label(
                thumb_strip, image=ph if ph else None,
                bg="#2C2C2C", relief="flat", bd=2, cursor="hand2",
            )
            lbl.pack(side="left", padx=(0, 4))
            lbl.bind("<Button-1>", lambda e, i=i: _go_to(i))
            thumb_labels.append(lbl)

        # ── Navegación ────────────────────────────────────────────────────
        def _go_to(idx: int):
            idx = idx % len(paths)
            state["idx"] = idx
            counter_var.set(f"{idx + 1} / {len(paths)}")

            lb.update_idletasks()
            cw = max(img_canvas.winfo_width(), 400)
            ch = max(img_canvas.winfo_height(), 320)
            result = W.load_image_fit(paths[idx], cw - 4, ch - 4)
            img_canvas.delete("all")
            if result:
                photo, pw, ph_ = result
                state["main_photo"] = photo
                img_canvas.create_image(cw // 2, ch // 2, anchor="center", image=photo)
            else:
                img_canvas.create_text(
                    cw // 2, ch // 2, text="Sin imagen",
                    fill="#666", font=(S.FONT_FAMILY, 12),
                )

            for i, lbl in enumerate(thumb_labels):
                lbl.config(
                    bg=S.PRIMARY if i == idx else "#2C2C2C",
                    relief="solid" if i == idx else "flat",
                )

            lb.update_idletasks()
            strip_w = thumb_strip.winfo_width()
            if strip_w > 0 and thumb_labels:
                lbl_x = thumb_labels[idx].winfo_x()
                lbl_w = thumb_labels[idx].winfo_width()
                viewport_w = thumb_canvas.winfo_width()
                frac = max(0.0, min(1.0, (lbl_x + lbl_w / 2 - viewport_w / 2) / strip_w))
                thumb_canvas.xview_moveto(frac)

        btn_prev.config(command=lambda: _go_to(state["idx"] - 1))
        btn_next.config(command=lambda: _go_to(state["idx"] + 1))
        img_canvas.bind("<Configure>", lambda e: _go_to(state["idx"]))
        lb.bind("<Left>",  lambda e: _go_to(state["idx"] - 1))
        lb.bind("<Right>", lambda e: _go_to(state["idx"] + 1))
        lb.bind("<Escape>", lambda e: lb.destroy())

        lb.update_idletasks()
        sw, sh = lb.winfo_screenwidth(), lb.winfo_screenheight()
        w, h = max(lb.winfo_width(), 720), max(lb.winfo_height(), 560)
        lb.geometry(f"{w}x{h}+{(sw - w)//2}+{(sh - h)//2}")

        _go_to(start_index)

    def _on_agregar_venta(self):
        """Pide cantidad y agrega la variante seleccionada a la venta activa."""
        key   = (self._talla_sel, self._color_sel)
        stock = self._combo_stock.get(key, 0)
        vid   = self._combo_id.get(key)
        p     = self._product
        parts = [x for x in [self._talla_sel, self._color_sel] if x]
        desc  = " / ".join(parts)

        win = tk.Toplevel(self)
        win.title("Cantidad a agregar")
        win.configure(bg=S.BG)
        win.resizable(False, False)
        win.grab_set()

        body = tk.Frame(win, bg=S.BG, padx=24, pady=16)
        body.pack()
        tk.Label(body, text=f"{p.nombre}  [{desc}]",
                 bg=S.BG, fg=S.PRIMARY_DARK,
                 font=(S.FONT_FAMILY, S.FONT_SIZE_MD, "bold")).pack(anchor="w", pady=(0, 4))
        tk.Label(body, text=f"Stock disponible: {stock} unidad(es)",
                 bg=S.BG, fg=S.TEXT_MEDIUM,
                 font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "italic")).pack(anchor="w", pady=(0, 10))

        qty_row = tk.Frame(body, bg=S.BG)
        qty_row.pack(anchor="w")
        tk.Label(qty_row, text="Cantidad:", bg=S.BG, fg=S.TEXT_DARK,
                 font=(S.FONT_FAMILY, S.FONT_SIZE_MD, "bold")).pack(side="left", padx=(0, 10))
        qty_var = tk.StringVar(value="1")
        qty_entry = tk.Entry(qty_row, textvariable=qty_var,
                             **S.ENTRY_STYLE, width=6, justify="center")
        qty_entry.pack(side="left")
        qty_entry.select_range(0, tk.END)
        qty_entry.focus_set()

        def _confirmar():
            try:
                qty = int(qty_var.get())
                if qty <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Inválido", "Ingresá una cantidad mayor a 0.", parent=win)
                return
            if qty > stock:
                messagebox.showerror(
                    "Stock insuficiente",
                    f"Solo hay {stock} unidad(es) disponibles.",
                    parent=win,
                )
                return
            from src.models.venta import VentaItem
            from src.services.venta_service import venta_service
            venta = venta_service.obtener_o_crear_abierta()
            nombre_label = f"{p.nombre} [{desc}]" if desc else p.nombre
            nuevos = list(venta.items)
            for item in nuevos:
                if item.producto_id == p.id and item.variante_id == vid:
                    item.cantidad += qty
                    item.subtotal = round(item.precio_unitario * item.cantidad, 2)
                    break
            else:
                nuevos.append(VentaItem(
                    producto_id=p.id,
                    nombre_producto=nombre_label,
                    precio_unitario=p.precio_unitario,
                    cantidad=qty,
                    variante_id=vid,
                ))
            venta_service.sync_items(venta.id, nuevos)
            win.destroy()
            messagebox.showinfo(
                "Agregado",
                f"{qty} x {nombre_label} agregado a la venta #{venta.id}.",
                parent=self,
            )

        btns = tk.Frame(win, bg=S.BG)
        btns.pack(fill="x", padx=24, pady=(4, 16))
        tk.Button(btns, text="Cancelar", **S.BTN_SECONDARY, command=win.destroy).pack(side="right")
        tk.Button(btns, text="\u2714 Agregar", **S.BTN_PRIMARY, command=_confirmar).pack(side="right", padx=(0, 8))
        win.bind("<Return>", lambda e: _confirmar())
        win.update_idletasks()
        ww, wh = win.winfo_width(), win.winfo_height()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"{ww}x{wh}+{(sw-ww)//2}+{(sh-wh)//2}")
