"""
Sección Venta — carrito de compra.

- Siempre muestra la última venta abierta (persiste entre navegaciones).
- Permite buscar y agregar productos, asignar cliente, cambiar cantidades.
- Cierra la venta (requiere cliente + al menos 1 producto).
- Al cerrar se pueden agregar pagos opcionales.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
from tkcalendar import DateEntry

from src.models.venta import Venta, VentaItem
from src.services.venta_service import venta_service
from src.services.producto_service import producto_service
from src.services.cliente_service import cliente_service
from src.ui import styles as S
from src.ui import widgets as W
from src.ui.cliente_form_modal import ClienteFormModal


class VentaSection(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=S.BG, **kwargs)
        self._venta: Venta | None = None
        self._items: list[VentaItem] = []          # copia editable del carrito
        self._prod_cache: dict[int, object] = {}   # producto_id → Producto (caché para modal)
        self._build()

    # ── Construcción ──────────────────────────────────────────────────────

    def _build(self):
        # --- Cabecera ---
        header = tk.Frame(self, bg=S.BG, padx=16, pady=10)
        header.pack(fill="x")
        tk.Label(header, text="Nueva Venta", **S.LABEL_TITLE, padx=0).pack(side="left")
        self.lbl_nro = tk.Label(
            header, text="",
            bg=S.BG, fg=S.TEXT_LIGHT,
            font=(S.FONT_FAMILY, S.FONT_SIZE_LG),
        )
        self.lbl_nro.pack(side="left", padx=14)

        btn_frame = tk.Frame(header, bg=S.BG)
        btn_frame.pack(side="right")
        tk.Button(
            btn_frame, text="🗑 Cancelar venta",
            **S.BTN_DANGER, command=self._cancelar,
        ).pack(side="right", padx=(8, 0))
        self.btn_cerrar = tk.Button(
            btn_frame, text="✔ Cerrar venta",
            **S.BTN_SUCCESS, command=self._cerrar,
        )
        self.btn_cerrar.pack(side="right")

        # --- Layout de dos columnas ---
        body = tk.Frame(self, bg=S.BG)
        body.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        # ===== Columna izquierda: carrito =====
        left = tk.Frame(body, bg=S.BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        # Buscar producto
        search_row = tk.Frame(left, bg=S.BG)
        search_row.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        search_row.columnconfigure(1, weight=1)
        tk.Label(
            search_row, text="Agregar producto:",
            bg=S.BG, fg=S.TEXT_MEDIUM,
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))
        self._prod_search_var = tk.StringVar()
        self._prod_search_var.trace_add("write", self._on_product_search)
        self._prod_entry = tk.Entry(
            search_row, textvariable=self._prod_search_var,
            **S.ENTRY_STYLE, width=30,
        )
        self._prod_entry.grid(row=0, column=1, sticky="ew")

        # Dropdown de resultados de búsqueda
        self._prod_listbox_frame = tk.Frame(left, bg=S.BG_CARD, relief="solid", bd=1)
        self._prod_listbox = tk.Listbox(
            self._prod_listbox_frame,
            bg=S.BG_CARD, fg=S.TEXT_DARK,
            font=(S.FONT_FAMILY, S.FONT_SIZE_MD),
            relief="flat", bd=0, height=5, activestyle="none",
            selectbackground=S.PRIMARY_LIGHT,
        )
        self._prod_listbox.pack(fill="both", expand=True)
        self._prod_listbox.bind("<Double-1>", self._on_product_select)
        self._prod_listbox.bind("<Return>", self._on_product_select)
        self._prod_results: list = []  # productos encontrados

        # Tabla carrito
        cols = ("nombre", "precio", "cant", "subtotal", "")
        self.cart_tree = ttk.Treeview(
            left, columns=cols, show="headings",
            height=12, selectmode="browse",
        )
        style = ttk.Style()
        style.configure("Cart.Treeview", rowheight=26, font=(S.FONT_FAMILY, S.FONT_SIZE_MD), background=S.BG_CARD, fieldbackground=S.BG_CARD)
        style.configure("Cart.Treeview.Heading", background=S.BG_SIDEBAR, foreground=S.PRIMARY_DARK, font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "bold"), relief="flat")
        style.map("Cart.Treeview", background=[("selected", S.PRIMARY_LIGHT)])
        self.cart_tree.configure(style="Cart.Treeview")
        for col, heading, width, anchor in [
            ("nombre",   "Producto",        260, "w"),
            ("precio",   "Precio unit.",     90, "e"),
            ("cant",     "Cant.",            60, "center"),
            ("subtotal", "Subtotal",         90, "e"),
            ("",         "",                 50, "center"),
        ]:
            self.cart_tree.heading(col, text=heading)
            self.cart_tree.column(col, width=width, anchor=anchor, stretch=(col == "nombre"))

        cart_scroll = ttk.Scrollbar(left, orient="vertical", command=self.cart_tree.yview)
        self.cart_tree.configure(yscrollcommand=cart_scroll.set)
        self.cart_tree.grid(row=1, column=0, sticky="nsew")
        cart_scroll.grid(row=1, column=1, sticky="ns")

        self.cart_tree.bind("<Double-1>", self._on_cart_double_click)

        # Total
        total_row = tk.Frame(left, bg=S.BG)
        total_row.grid(row=2, column=0, columnspan=2, sticky="e", pady=(8, 0))
        tk.Label(
            total_row, text="Total:",
            bg=S.BG, fg=S.TEXT_MEDIUM,
            font=(S.FONT_FAMILY, S.FONT_SIZE_LG, "bold"),
        ).pack(side="left", padx=(0, 8))
        self._total_var = tk.StringVar(value="$0.00")
        tk.Label(
            total_row, textvariable=self._total_var,
            bg=S.BG, fg=S.PRIMARY_DARK,
            font=(S.FONT_FAMILY, FONT_SIZE_TOTAL := 20, "bold"),
        ).pack(side="left")

        # ===== Columna derecha: cliente =====
        right = tk.Frame(body, bg=S.BG_CARD, relief="solid", bd=1)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)

        tk.Label(
            right, text="Cliente",
            bg=S.BG_CARD, fg=S.PRIMARY_DARK,
            font=(S.FONT_FAMILY, S.FONT_SIZE_LG, "bold"),
        ).pack(anchor="w", padx=12, pady=(10, 4))

        tk.Frame(right, bg=S.BORDER, height=1).pack(fill="x")

        # Buscar cliente
        cli_search_frame = tk.Frame(right, bg=S.BG_CARD)
        cli_search_frame.pack(fill="x", padx=10, pady=8)
        self._cli_search_var = tk.StringVar()
        self._cli_search_var.trace_add("write", self._on_client_search)
        tk.Label(
            cli_search_frame, text="Buscar:",
            bg=S.BG_CARD, fg=S.TEXT_MEDIUM,
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM),
        ).pack(anchor="w")
        tk.Entry(
            cli_search_frame, textvariable=self._cli_search_var,
            **S.ENTRY_STYLE, width=22,
        ).pack(fill="x")

        self._cli_listbox = tk.Listbox(
            right,
            bg=S.BG_CARD, fg=S.TEXT_DARK,
            font=(S.FONT_FAMILY, S.FONT_SIZE_MD),
            relief="flat", bd=0, height=5, activestyle="none",
            selectbackground=S.PRIMARY_LIGHT,
        )
        self._cli_listbox.pack(fill="x", padx=4)
        self._cli_listbox.bind("<<ListboxSelect>>", self._on_client_select)
        self._cli_results: list = []

        tk.Frame(right, bg=S.BORDER, height=1).pack(fill="x", pady=(4, 0))

        # Cliente seleccionado
        self._cli_name_var = tk.StringVar(value="Sin asignar")
        tk.Label(
            right, text="Asignado:",
            bg=S.BG_CARD, fg=S.TEXT_MEDIUM,
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "bold"),
        ).pack(anchor="w", padx=12, pady=(8, 0))
        tk.Label(
            right, textvariable=self._cli_name_var,
            bg=S.BG_CARD, fg=S.PRIMARY_DARK,
            font=(S.FONT_FAMILY, S.FONT_SIZE_MD, "bold"),
            wraplength=180, justify="left",
        ).pack(anchor="w", padx=12)
        tk.Button(
            right, text="⊕ Nuevo cliente",
            bg=S.BG_CARD, fg=S.SUCCESS,
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM),
            relief="flat", bd=0, cursor="hand2",
            command=self._nuevo_cliente,
        ).pack(anchor="w", padx=12, pady=(2, 0))
        tk.Button(
            right, text="✕ Quitar cliente",
            bg=S.BG_CARD, fg=S.DANGER,
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM),
            relief="flat", bd=0, cursor="hand2",
            command=self._quitar_cliente,
        ).pack(anchor="w", padx=12, pady=(4, 0))

    # ── Refresh (llamado al volver a la sección) ───────────────────────────

    def refresh(self):
        self._venta = venta_service.obtener_o_crear_abierta()
        self._items = list(self._venta.items)
        self._render_cart()
        self._render_cliente()
        self.lbl_nro.config(text=f"# {self._venta.id}")

    # ── Producto search ───────────────────────────────────────────────────

    def _on_product_search(self, *_):
        q = self._prod_search_var.get().strip()
        self._prod_listbox_frame.place_forget()
        if len(q) < 1:
            return
        productos, _ = producto_service.listar_paginado(search=q, page=1, page_size=8)
        self._prod_results = productos
        self._prod_listbox.delete(0, tk.END)
        for p in productos:
            self._prod_listbox.insert(tk.END, f"{p.nombre}  ({S.fmt_moneda(p.precio_unitario)})")
        if productos:
            # Posicionar el listbox debajo del entry
            ex = self._prod_entry.winfo_x() + self._prod_entry.master.winfo_x()
            ey = self._prod_entry.winfo_y() + self._prod_entry.master.winfo_y() + self._prod_entry.winfo_height() + 2
            self._prod_listbox_frame.place(x=ex, y=ey, width=self._prod_entry.winfo_width() + 200)
            self._prod_listbox_frame.lift()

    def _on_product_select(self, event=None):
        idx = self._prod_listbox.curselection()
        if not idx:
            return
        prod = self._prod_results[idx[0]]
        self._prod_listbox_frame.place_forget()
        self._prod_search_var.set("")
        # Los resultados de búsqueda ya traen variantes; cachear para reuso
        self._prod_cache[prod.id] = prod
        SeleccionVarianteModal(self, prod, on_confirm=self._agregar_item_desde_modal)

    def _agregar_item_desde_modal(self, producto_id, variante_id, variante_desc, nombre, precio, cantidad):
        """Callback del SeleccionVarianteModal: agrega o actualiza el ítem en el carrito."""
        nombre_label = f"{nombre} [{variante_desc}]" if variante_desc else nombre
        for item in self._items:
            if item.producto_id == producto_id and item.variante_id == variante_id:
                item.cantidad = cantidad
                item.subtotal = round(item.precio_unitario * cantidad, 2)
                self._save_and_render()
                return
        self._items.append(VentaItem(
            producto_id=producto_id,
            nombre_producto=nombre_label,
            precio_unitario=precio,
            cantidad=cantidad,
            variante_id=variante_id,
        ))
        self._save_and_render()

    # ── Carrito ───────────────────────────────────────────────────────────

    def _render_cart(self):
        self.cart_tree.delete(*self.cart_tree.get_children())
        for i, item in enumerate(self._items):
            self.cart_tree.insert("", "end", iid=str(i), values=(
                item.nombre_producto,
                S.fmt_moneda(item.precio_unitario),
                item.cantidad,
                S.fmt_moneda(item.subtotal),
                "✕",
            ))
        total = sum(i.subtotal for i in self._items)
        self._total_var.set(S.fmt_moneda(total))

    def _on_cart_double_click(self, event):
        region = self.cart_tree.identify_region(event.x, event.y)
        col    = self.cart_tree.identify_column(event.x)
        item   = self.cart_tree.identify_row(event.y)
        if not item:
            return
        idx = int(item)
        if col == "#5":
            self._items.pop(idx)
            self._save_and_render()
        else:
            cart_item = self._items[idx]
            prod = self._prod_cache.get(cart_item.producto_id)
            if prod is None:
                prod = producto_service.obtener_por_id(cart_item.producto_id)
                if prod:
                    self._prod_cache[prod.id] = prod
            if prod:
                SeleccionVarianteModal(
                    self, prod,
                    on_confirm=self._agregar_item_desde_modal,
                    cantidad_actual=cart_item.cantidad,
                    variante_id_actual=cart_item.variante_id,
                )

    # ── Cliente ───────────────────────────────────────────────────────────

    def _on_client_search(self, *_):
        q = self._cli_search_var.get().strip()
        self._cli_listbox.delete(0, tk.END)
        self._cli_results = []
        if len(q) < 1:
            return
        clientes, _ = cliente_service.listar_paginado(search=q, page=1, page_size=8)
        self._cli_results = clientes
        for c in clientes:
            self._cli_listbox.insert(tk.END, f"{c.nombre}  ({c.telefono})")

    def _on_client_select(self, event=None):
        idx = self._cli_listbox.curselection()
        if not idx or not self._venta:
            return
        c = self._cli_results[idx[0]]
        self._venta.cliente_id = c.id
        self._venta.nombre_cliente = c.nombre
        venta_service.set_cliente(self._venta.id, c.id, c.nombre)
        self._render_cliente()
        self._cli_search_var.set("")
        self._cli_listbox.delete(0, tk.END)

    def _quitar_cliente(self):
        if self._venta:
            self._venta.cliente_id = None
            self._venta.nombre_cliente = ""
            venta_service.set_cliente(self._venta.id, None, "")
            self._render_cliente()

    def _nuevo_cliente(self):
        """Abre el formulario de nuevo cliente y lo asigna a la venta al guardar."""
        def _on_creado(cliente=None):
            if cliente and self._venta:
                self._venta.cliente_id = cliente.id
                self._venta.nombre_cliente = cliente.nombre
                venta_service.set_cliente(self._venta.id, cliente.id, cliente.nombre)
                self._render_cliente()
        ClienteFormModal(self, cliente=None, on_save=_on_creado)

    def _render_cliente(self):
        if self._venta and self._venta.nombre_cliente:
            self._cli_name_var.set(self._venta.nombre_cliente)
        else:
            self._cli_name_var.set("Sin asignar")

    # ── Persistencia + render ─────────────────────────────────────────────

    def _save_and_render(self):
        if self._venta:
            venta_service.sync_items(self._venta.id, self._items)
        self._render_cart()

    # ── Acciones principales ──────────────────────────────────────────────

    def _cancelar(self):
        if not self._venta:
            return
        if not messagebox.askyesno(
            "Cancelar venta",
            "¿Eliminar la venta en curso?\nSe perderán todos los productos agregados.",
            parent=self,
        ):
            return
        venta_service.cancelar(self._venta.id)
        self._venta = None
        self._items = []
        self.refresh()

    def _cerrar(self):
        if not self._venta:
            return
        try:
            # Validar antes de abrir el modal de pagos
            venta_service.cerrar.__doc__  # touch
            if not self._items:
                raise ValueError("Debe agregar al menos un producto.")
            if not self._venta.cliente_id:
                raise ValueError("Debe asignar un cliente.")
        except ValueError as exc:
            messagebox.showerror("No se puede cerrar", str(exc), parent=self)
            return

        CerrarVentaModal(self, self._venta, on_cerrada=self._post_cierre)

    def _post_cierre(self):
        self._venta = None
        self._items = []
        self.refresh()


# ── Modal de cierre de venta (pagos opcionales) ────────────────────────────

class CerrarVentaModal(tk.Toplevel):
    def __init__(self, parent, venta: Venta, on_cerrada=None):
        super().__init__(parent)
        self.title(f"Cerrar Venta #{venta.id}")
        self.configure(bg=S.BG)
        self.resizable(False, False)
        self._venta = venta
        self._on_cerrada = on_cerrada
        self._pagos_nuevos: list[dict] = []
        self._build()
        self.grab_set()
        self._center()

    def _center(self):
        self.update_idletasks()
        w, h = max(self.winfo_width(), 460), max(self.winfo_height(), 400)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _build(self):
        v = self._venta
        # Header
        header = tk.Frame(self, bg=S.PRIMARY, padx=20, pady=10)
        header.pack(fill="x")
        tk.Label(
            header, text=f"Cerrar Venta #{v.id}",
            bg=S.PRIMARY, fg="white",
            font=(S.FONT_FAMILY, S.FONT_SIZE_LG, "bold"),
        ).pack(side="left")
        tk.Label(
            header, text=f"Total: {S.fmt_moneda(v.total)}",
            bg=S.PRIMARY, fg=S.PRIMARY_LIGHT,
            font=(S.FONT_FAMILY, S.FONT_SIZE_MD),
        ).pack(side="right")

        body = tk.Frame(self, bg=S.BG, padx=20, pady=12)
        body.pack(fill="both", expand=True)

        # Resumen
        tk.Label(
            body, text=f"Cliente: {v.nombre_cliente}",
            bg=S.BG, fg=S.TEXT_DARK,
            font=(S.FONT_FAMILY, S.FONT_SIZE_MD),
        ).pack(anchor="w")
        tk.Label(
            body, text=f"{len(v.items)} producto(s) — Total: {S.fmt_moneda(v.total)}",
            bg=S.BG, fg=S.TEXT_MEDIUM,
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM),
        ).pack(anchor="w", pady=(0, 10))

        tk.Frame(body, bg=S.BORDER, height=1).pack(fill="x", pady=(0, 10))

        # Agregar pago
        tk.Label(
            body, text="Agregar pago (opcional):",
            bg=S.BG, fg=S.PRIMARY_DARK,
            font=(S.FONT_FAMILY, S.FONT_SIZE_MD, "bold"),
        ).pack(anchor="w")

        pago_row = tk.Frame(body, bg=S.BG)
        pago_row.pack(fill="x", pady=(6, 0))

        tk.Label(pago_row, text="Monto $", bg=S.BG, fg=S.TEXT_MEDIUM,
                 font=(S.FONT_FAMILY, S.FONT_SIZE_SM)).grid(row=0, column=0, sticky="w", pady=2)
        self._monto_var = tk.StringVar()
        monto_frame = tk.Frame(pago_row, bg=S.BG)
        monto_frame.grid(row=0, column=1, sticky="w", padx=(6, 16), pady=2)
        tk.Entry(monto_frame, textvariable=self._monto_var, **S.ENTRY_STYLE, width=12).pack(side="left")
        self._btn_saldo = tk.Button(
            monto_frame, text="Pagar saldo",
            bg=S.BG_SIDEBAR, fg=S.PRIMARY_DARK,
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM),
            relief="flat", bd=0, padx=8, cursor="hand2",
            command=self._pagar_saldo_restante,
        )
        self._btn_saldo.pack(side="left", padx=(8, 0))

        tk.Label(pago_row, text="Tipo", bg=S.BG, fg=S.TEXT_MEDIUM,
                 font=(S.FONT_FAMILY, S.FONT_SIZE_SM)).grid(row=0, column=2, sticky="w", pady=2)
        self._tipo_var = tk.StringVar(value="efectivo")
        ttk.Combobox(
            pago_row, textvariable=self._tipo_var,
            values=["efectivo", "transferencia", "tarjeta"],
            state="readonly", width=14,
            font=(S.FONT_FAMILY, S.FONT_SIZE_MD),
        ).grid(row=0, column=3, sticky="w", padx=(6, 0), pady=2)

        tk.Label(pago_row, text="Fecha", bg=S.BG, fg=S.TEXT_MEDIUM,
                 font=(S.FONT_FAMILY, S.FONT_SIZE_SM)).grid(row=1, column=0, sticky="w", pady=2)
        self._fecha_entry = DateEntry(
            pago_row, width=12, background=S.PRIMARY, foreground="white",
            borderwidth=2, date_pattern="yyyy-mm-dd",
            font=(S.FONT_FAMILY, S.FONT_SIZE_MD),
        )
        self._fecha_entry.set_date(date.today())
        self._fecha_entry.grid(row=1, column=1, sticky="w", padx=(6, 0), pady=2)

        tk.Button(
            body, text="+ Agregar pago",
            **S.BTN_SECONDARY, command=self._agregar_pago,
        ).pack(anchor="w", pady=(8, 4))

        # Lista de pagos añadidos
        self._pagos_frame = tk.Frame(body, bg=S.BG)
        self._pagos_frame.pack(fill="x")
        self._saldo_var = tk.StringVar()
        self._saldo_lbl = tk.Label(
            body, textvariable=self._saldo_var,
            bg=S.BG, fg=S.PRIMARY_DARK,
            font=(S.FONT_FAMILY, S.FONT_SIZE_MD, "bold"),
        )
        self._saldo_lbl.pack(anchor="e", pady=(6, 0))
        self._refresh_pagos_ui()

        # Footer
        btn_frame = tk.Frame(self, bg=S.BG)
        btn_frame.pack(fill="x", padx=20, pady=(4, 16))
        tk.Button(btn_frame, text="Cancelar", **S.BTN_SECONDARY, command=self.destroy).pack(side="right")
        tk.Button(
            btn_frame, text="✔ Confirmar cierre",
            **S.BTN_PRIMARY, command=self._confirmar,
        ).pack(side="right", padx=(0, 8))

    def _agregar_pago(self):
        try:
            monto = float(self._monto_var.get().replace(",", "."))
            if monto <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Monto inválido", "Ingresá un monto mayor a 0.",parent=self)
            return
        self._pagos_nuevos.append({
            "monto": monto,
            "tipo": self._tipo_var.get(),
            "fecha": self._fecha_entry.get_date().strftime("%Y-%m-%d"),
        })
        self._monto_var.set("")
        self._refresh_pagos_ui()

    def _pagar_saldo_restante(self):
        total_ya = sum(p["monto"] for p in self._pagos_nuevos)
        saldo = self._venta.total - total_ya
        if saldo > 0:
            self._monto_var.set(f"{saldo:.2f}")

    def _refresh_pagos_ui(self):
        for w in self._pagos_frame.winfo_children():
            w.destroy()
        for i, p in enumerate(self._pagos_nuevos):
            row = tk.Frame(self._pagos_frame, bg=S.BG)
            row.pack(fill="x", pady=1)
            tk.Label(
                row,
                text=f"  {S.fmt_moneda(p['monto'])}  —  {p['tipo']}  ({p['fecha']})",
                bg=S.BG, fg=S.TEXT_DARK,
                font=(S.FONT_FAMILY, S.FONT_SIZE_SM),
            ).pack(side="left")
            tk.Button(
                row, text="✕",
                bg=S.BG, fg=S.DANGER,
                font=(S.FONT_FAMILY, S.FONT_SIZE_SM),
                relief="flat", bd=0, cursor="hand2",
                command=lambda idx=i: self._quitar_pago(idx),
            ).pack(side="left", padx=4)
        total_pago = sum(p["monto"] for p in self._pagos_nuevos)
        saldo = self._venta.total - total_pago
        color = S.SUCCESS if saldo <= 0 else S.WARNING
        self._saldo_var.set(f"Pagado: {S.fmt_moneda(total_pago)}  |  Saldo: {S.fmt_moneda(saldo)}")
        self._saldo_lbl.config(fg=color)

    def _quitar_pago(self, idx):
        self._pagos_nuevos.pop(idx)
        self._refresh_pagos_ui()

    def _confirmar(self):
        try:
            venta_service.cerrar(self._venta.id)
        except ValueError as exc:
            messagebox.showerror("Error", str(exc), parent=self)
            return
        for p in self._pagos_nuevos:
            venta_service.agregar_pago(
                self._venta.id, p["monto"], p["tipo"], p["fecha"]
            )
        self.destroy()
        if self._on_cerrada:
            self._on_cerrada()


# ── Modal de selección de variante y cantidad ──────────────────────────────

class SeleccionVarianteModal(tk.Toplevel):
    """
    Modal que aparece al elegir un producto durante la venta.
    Muestra pills de Talla y Color con la misma interactividad que
    ProductDetailModal: seleccionar talla filtra los colores disponibles.
    Valida stock al confirmar.
    """

    def __init__(self, parent, producto, on_confirm,
                 cantidad_actual: int = 0, variante_id_actual=None):
        super().__init__(parent)
        self._producto           = producto
        self._on_confirm         = on_confirm
        self._cantidad_actual    = cantidad_actual
        self._variante_id_actual = variante_id_actual

        # Estado de selección de pills (igual que ProductDetailModal)
        self._talla_sel: str | None = None
        self._color_sel: str | None = None
        self._pill_talla: dict[str, tk.Button] = {}
        self._pill_color: dict[str, tk.Button] = {}

        # Mapas de relación variante ↔ talla/color/stock
        from collections import defaultdict
        self._talla_colors: dict = defaultdict(set)
        self._combo_stock:  dict = {}
        self._combo_id:     dict = {}   # {(talla, color): variante_id}
        for v in producto.variantes:
            self._talla_colors[v.talla].add(v.color)
            self._combo_stock[(v.talla, v.color)] = v.stock
            self._combo_id[(v.talla, v.color)]    = v.id

        self._build()
        self.grab_set()

        # Pre-selección si viene de editar un ítem del carrito
        if variante_id_actual is not None:
            for v in producto.variantes:
                if v.id == variante_id_actual:
                    self._talla_sel = v.talla
                    self._color_sel = v.color
                    self._refresh_pills()
                    break
        elif len(producto.variantes) == 1 and producto.variantes[0].stock > 0:
            v = producto.variantes[0]
            self._talla_sel = v.talla
            self._color_sel = v.color
            self._refresh_pills()

        self._center()

    def _center(self):
        self.update_idletasks()
        w = max(self.winfo_width(), 440)
        h = max(self.winfo_height(), 320)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    # ── Construcción ─────────────────────────────────────────────────────

    def _build(self):
        p = self._producto
        self.title(f"Agregar — {p.nombre}")
        self.configure(bg=S.BG)
        self.resizable(False, False)

        # Header
        hdr = tk.Frame(self, bg=S.PRIMARY, padx=20, pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text=p.nombre, bg=S.PRIMARY, fg="white",
                 font=(S.FONT_FAMILY, S.FONT_SIZE_LG, "bold")).pack(side="left")
        tk.Label(hdr, text=S.fmt_moneda(p.precio_unitario), bg=S.PRIMARY, fg=S.PRIMARY_LIGHT,
                 font=(S.FONT_FAMILY, S.FONT_SIZE_MD)).pack(side="right")

        body = tk.Frame(self, bg=S.BG, padx=20, pady=14)
        body.pack(fill="both", expand=True)

        if p.variantes:
            tallas  = sorted(self._talla_colors.keys())
            colores = sorted({v.color for v in p.variantes})

            # ── Talles ──
            if any(t for t in tallas):   # solo mostrar si hay talles no vacíos
                tk.Label(body, text="Talle:",
                         bg=S.BG, fg=S.TEXT_MEDIUM,
                         font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "bold")).pack(anchor="w", pady=(0, 4))
                tallas_frame = tk.Frame(body, bg=S.BG)
                tallas_frame.pack(anchor="w", pady=(0, 8))
                for t in tallas:
                    btn = self._make_pill(tallas_frame, t, self._toggle_talla)
                    btn.pack(side="left", padx=(0, 6), pady=2)
                    self._pill_talla[t] = btn

            # ── Colores ──
            if any(c for c in colores):  # solo mostrar si hay colores no vacíos
                tk.Label(body, text="Color:",
                         bg=S.BG, fg=S.TEXT_MEDIUM,
                         font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "bold")).pack(anchor="w", pady=(0, 4))
                colores_frame = tk.Frame(body, bg=S.BG)
                colores_frame.pack(anchor="w", pady=(0, 8))
                for c in colores:
                    btn = self._make_pill(colores_frame, c, self._toggle_color)
                    btn.pack(side="left", padx=(0, 6), pady=2)
                    self._pill_color[c] = btn

            # Stock disponible para la selección actual
            stock_row = tk.Frame(body, bg=S.BG)
            stock_row.pack(anchor="w", pady=(0, 4))
            tk.Label(stock_row, text="Disponible:",
                     bg=S.BG, fg=S.TEXT_MEDIUM,
                     font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "bold")).pack(side="left", padx=(0, 8))
            self._stock_var = tk.StringVar(value="—")
            self._stock_lbl = tk.Label(stock_row, textvariable=self._stock_var,
                                        bg=S.BG, fg=S.PRIMARY_DARK,
                                        font=(S.FONT_FAMILY, S.FONT_SIZE_MD, "bold"))
            self._stock_lbl.pack(side="left")
        else:
            tk.Label(body, text="Este producto no tiene variantes definidas.",
                     bg=S.BG, fg=S.TEXT_LIGHT,
                     font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "italic")).pack(anchor="w", pady=(0, 10))

        # ── Cantidad ──
        qty_row = tk.Frame(body, bg=S.BG)
        qty_row.pack(anchor="w", pady=(10, 4))
        tk.Label(qty_row, text="Cantidad:", bg=S.BG, fg=S.TEXT_DARK,
                 font=(S.FONT_FAMILY, S.FONT_SIZE_MD, "bold")).pack(side="left", padx=(0, 10))
        self._qty_var = tk.StringVar(value=str(max(1, self._cantidad_actual)))
        self._qty_entry = tk.Entry(qty_row, textvariable=self._qty_var,
                                   **S.ENTRY_STYLE, width=6, justify="center")
        self._qty_entry.pack(side="left")
        self._max_lbl = tk.Label(qty_row, text="", bg=S.BG, fg=S.TEXT_LIGHT,
                                  font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "italic"))
        self._max_lbl.pack(side="left", padx=(8, 0))

        # ── Botones ──
        btns = tk.Frame(self, bg=S.BG)
        btns.pack(fill="x", padx=20, pady=(4, 16))
        tk.Button(btns, text="Cancelar", **S.BTN_SECONDARY, command=self.destroy).pack(side="right")
        tk.Button(btns, text="✔ Agregar al carrito",
                  **S.BTN_PRIMARY, command=self._confirmar).pack(side="right", padx=(0, 8))

        self._qty_entry.focus_set()
        self.bind("<Return>", lambda e: self._confirmar())

    # ── Pills (mismo estilo que ProductDetailModal) ───────────────────────

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
        return {v.color for v in self._producto.variantes}

    def _refresh_pills(self):
        avail_colors = self._available_colors()

        for t, btn in self._pill_talla.items():
            btn.config(bg=S.PRIMARY if t == self._talla_sel else S.BG_SIDEBAR,
                       fg="white"   if t == self._talla_sel else S.TEXT_DARK)

        for c, btn in self._pill_color.items():
            if c not in avail_colors:
                btn.config(bg="#EEEEEE", fg=S.TEXT_LIGHT, cursor="arrow")
            elif c == self._color_sel:
                btn.config(bg=S.PRIMARY, fg="white", cursor="hand2")
            else:
                btn.config(bg=S.BG_SIDEBAR, fg=S.TEXT_DARK, cursor="hand2")

        self._update_stock_label()

    def _update_stock_label(self):
        if not hasattr(self, "_stock_var"):
            return
        t, c = self._talla_sel, self._color_sel
        if t and c:
            stock = self._combo_stock.get((t, c), 0)
            color = S.SUCCESS if stock > 0 else S.DANGER
            self._stock_var.set(f"{stock} unidad(es)")
            self._stock_lbl.config(fg=color)
            self._max_lbl.config(text=f"(máx. {stock})")
        elif t:
            stock = sum(v.stock for v in self._producto.variantes if v.talla == t)
            self._stock_var.set(f"{stock}  (todos los colores de talle {t})")
            self._stock_lbl.config(fg=S.TEXT_MEDIUM)
            self._max_lbl.config(text="")
        elif c:
            stock = sum(v.stock for v in self._producto.variantes if v.color == c)
            self._stock_var.set(f"{stock}  (todos los talles en {c})")
            self._stock_lbl.config(fg=S.TEXT_MEDIUM)
            self._max_lbl.config(text="")
        else:
            self._stock_var.set("—  (seleccioná talle y color)")
            self._stock_lbl.config(fg=S.TEXT_LIGHT)
            self._max_lbl.config(text="")

    # ── Confirmar ────────────────────────────────────────────────────────

    def _confirmar(self):
        p = self._producto
        if p.variantes:
            # Necesitamos que quede determinada una sola variante
            key = (self._talla_sel, self._color_sel)
            variante_id = self._combo_id.get(key)
            if variante_id is None:
                messagebox.showerror(
                    "Falta selección",
                    "Seleccioná talle y color para continuar.",
                    parent=self,
                )
                return
            stock = self._combo_stock.get(key, 0)
        else:
            variante_id = None
            stock       = None   # sin límite

        try:
            qty = int(self._qty_var.get())
            if qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Cantidad inválida",
                                 "La cantidad debe ser un número entero mayor a 0.", parent=self)
            return

        if stock is not None and qty > stock:
            messagebox.showerror(
                "Stock insuficiente",
                f"Solo hay {stock} unidad(es) disponibles de esa variante.",
                parent=self,
            )
            return

        parts = [x for x in [self._talla_sel, self._color_sel] if x]
        variante_desc = " / ".join(parts)

        self.destroy()
        self._on_confirm(
            p.id,
            variante_id,
            variante_desc,
            p.nombre,
            p.precio_unitario,
            qty,
        )
