"""
Modal de detalle de una venta cerrada (factura).
Muestra: datos del cliente, items, pagos, saldo.
Permite agregar/quitar pagos y registrar devoluciones.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
from tkcalendar import DateEntry

from src.models.venta import Venta, Pago, VentaItem
from src.services.venta_service import venta_service
from src.services.devolucion_service import devolucion_service
from src.ui import styles as S
from src.ui import widgets as W


class VentaDetailModal(tk.Toplevel):
    def __init__(self, parent, venta: Venta, on_change=None):
        super().__init__(parent)
        self.title(f"Venta #{venta.id}")
        self.configure(bg=S.BG)
        self.resizable(True, True)
        self.minsize(560, 500)
        self._venta = venta
        self._on_change = on_change
        self._build()
        self._center()
        self.grab_set()

    def _center(self):
        self.update_idletasks()
        w = max(self.winfo_width(), 580)
        h = max(self.winfo_height(), 520)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    # ── Build ─────────────────────────────────────────────────────────────

    def _build(self):
        v = self._venta
        # Header
        header = tk.Frame(self, bg=S.PRIMARY, padx=20, pady=12)
        header.pack(fill="x")
        tk.Label(
            header, text=f"Venta #{v.id}",
            bg=S.PRIMARY, fg="white",
            font=(S.FONT_FAMILY, S.FONT_SIZE_TITLE, "bold"),
        ).pack(side="left")
        estado_color = S.SUCCESS if v.estado == "cerrada" else S.WARNING
        tk.Label(
            header, text=v.estado.upper(),
            bg=estado_color, fg="white",
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "bold"),
            padx=8, pady=2,
        ).pack(side="right")

        # Body scrollable
        outer, _, body = W.make_scrollable_frame(self, bg=S.BG)
        outer.pack(fill="both", expand=True, padx=16, pady=10)

        # ── Info general ──
        info = tk.Frame(body, bg=S.BG)
        info.pack(fill="x", pady=(0, 10))
        info.columnconfigure(1, weight=1)

        def _row(label, value, row):
            tk.Label(info, text=label + ":", bg=S.BG, fg=S.TEXT_MEDIUM,
                     font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "bold"), anchor="w",
                     ).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=2)
            tk.Label(info, text=value, bg=S.BG, fg=S.TEXT_DARK,
                     font=(S.FONT_FAMILY, S.FONT_SIZE_MD), anchor="w",
                     ).grid(row=row, column=1, sticky="w", pady=2)

        _row("Cliente",       v.nombre_cliente or "-",               0)
        _row("Apertura",      v.fecha_apertura[:16] if v.fecha_apertura else "-", 1)
        _row("Cierre",        v.fecha_cierre[:16] if v.fecha_cierre else "-",     2)

        # ── Items ──
        tk.Label(body, text="Productos", bg=S.BG, fg=S.PRIMARY_DARK,
                 font=(S.FONT_FAMILY, S.FONT_SIZE_LG, "bold"),
                 ).pack(anchor="w", pady=(6, 4))

        self._items_container = tk.Frame(body, bg=S.BG)
        self._items_container.pack(fill="x")

        self._total_items_var = tk.StringVar()
        tk.Label(body, textvariable=self._total_items_var,
                 bg=S.BG, fg=S.PRIMARY_DARK,
                 font=(S.FONT_FAMILY, S.FONT_SIZE_LG, "bold"),
                 ).pack(anchor="e", pady=(4, 0))

        tk.Frame(body, bg=S.BORDER, height=1).pack(fill="x", pady=(12, 8))

        # ── Pagos ──
        pago_header = tk.Frame(body, bg=S.BG)
        pago_header.pack(fill="x")
        tk.Label(pago_header, text="Pagos", bg=S.BG, fg=S.PRIMARY_DARK,
                 font=(S.FONT_FAMILY, S.FONT_SIZE_LG, "bold"),
                 ).pack(side="left")
        tk.Button(
            pago_header, text="+ Agregar pago",
            **S.BTN_SECONDARY, command=self._agregar_pago,
        ).pack(side="right")

        self._pagos_container = tk.Frame(body, bg=S.BG)
        self._pagos_container.pack(fill="x", pady=(6, 0))

        # ── Balance ──
        tk.Frame(body, bg=S.BORDER, height=1).pack(fill="x", pady=(10, 6))
        self._balance_container = tk.Frame(body, bg=S.BG)
        self._balance_container.pack(fill="x")

        self._render_items()
        self._render_pagos()

        # Footer
        btn_frame = tk.Frame(self, bg=S.BG)
        btn_frame.pack(fill="x", padx=16, pady=(4, 16))
        tk.Button(btn_frame, text="Cerrar", **S.BTN_SECONDARY, command=self.destroy).pack(side="right")

    # ── Items render ──────────────────────────────────────────────────────

    def _render_items(self):
        for w in self._items_container.winfo_children():
            w.destroy()

        v = self._venta
        style = ttk.Style()
        style.configure("Detail.Treeview", rowheight=24, font=(S.FONT_FAMILY, S.FONT_SIZE_MD),
                         background=S.BG_CARD, fieldbackground=S.BG_CARD)
        style.configure("Detail.Treeview.Heading", background=S.BG_SIDEBAR,
                         foreground=S.PRIMARY_DARK, font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "bold"), relief="flat")
        style.map("Detail.Treeview", background=[("selected", S.BG_SIDEBAR)])

        cols = ("producto", "precio", "cant", "estado", "subtotal")
        tree = ttk.Treeview(
            self._items_container, columns=cols, show="headings",
            height=min(len(v.items) + 1, 8), style="Detail.Treeview",
        )
        tree.tag_configure("devuelto",  foreground=S.DANGER,   font=(S.FONT_FAMILY, S.FONT_SIZE_MD, "italic"))
        tree.tag_configure("parcial",   foreground=S.WARNING,  font=(S.FONT_FAMILY, S.FONT_SIZE_MD, "italic"))
        tree.tag_configure("normal",    foreground=S.TEXT_DARK)

        for col, heading, width, anchor in [
            ("producto", "Producto",     240, "w"),
            ("precio",   "Precio unit.",  90, "e"),
            ("cant",     "Cant.",          55, "center"),
            ("estado",   "Estado",        120, "center"),
            ("subtotal", "Subtotal",       90, "e"),
        ]:
            tree.heading(col, text=heading)
            tree.column(col, width=width, anchor=anchor, stretch=(col == "producto"))

        self._item_iids: dict[str, VentaItem] = {}  # iid → VentaItem
        for item in v.items:
            d = item.devolucion
            if d is None:
                estado_txt = "—"
                tag = "normal"
            elif d.cantidad_devuelta >= item.cantidad:
                estado_txt = "✓ Devuelto"
                tag = "devuelto"
            else:
                estado_txt = f"Dev. parcial ({d.cantidad_devuelta}/{item.cantidad})"
                tag = "parcial"

            iid = tree.insert("", "end", tags=(tag,), values=(
                item.nombre_producto,
                S.fmt_moneda(item.precio_unitario),
                item.cantidad,
                estado_txt,
                S.fmt_moneda(item.subtotal),
            ))
            self._item_iids[iid] = item

        tree.pack(fill="x")

        # Botón "Devolver ítem seleccionado"
        btn_row = tk.Frame(self._items_container, bg=S.BG)
        btn_row.pack(fill="x", pady=(4, 0))

        def _on_devolver():
            sel = tree.selection()
            if not sel:
                messagebox.showinfo("Selección", "Seleccioná un producto para devolver.", parent=self)
                return
            item = self._item_iids[sel[0]]
            if item.devolucion is not None and item.devolucion.cantidad_devuelta >= item.cantidad:
                messagebox.showinfo("Sin acción", "Este ítem ya fue completamente devuelto.", parent=self)
                return
            self._devolver_item(item)

        tk.Button(
            btn_row, text="↩ Devolver ítem seleccionado",
            bg=S.WARNING, fg="white",
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "bold"),
            relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
            command=_on_devolver,
        ).pack(side="right")

        self._total_items_var.set(f"Total venta: {S.fmt_moneda(v.total)}")

    # ── Devolución ────────────────────────────────────────────────────────

    def _devolver_item(self, item: VentaItem):
        """Abre el modal de confirmación de devolución para un ítem."""
        win = tk.Toplevel(self)
        win.title("Registrar devolución")
        win.configure(bg=S.BG)
        win.resizable(False, False)
        win.grab_set()

        body = tk.Frame(win, bg=S.BG, padx=20, pady=16)
        body.pack()
        body.columnconfigure(1, weight=1)

        row_i = [0]

        def _lbl(text):
            tk.Label(body, text=text, bg=S.BG, fg=S.TEXT_MEDIUM,
                     font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "bold"), anchor="w",
                     ).grid(row=row_i[0], column=0, sticky="w", padx=(0, 10), pady=4)

        # Info del ítem
        tk.Label(
            body,
            text=f"{item.nombre_producto}   ×{item.cantidad}   {S.fmt_moneda(item.subtotal)}",
            bg=S.BG, fg=S.PRIMARY_DARK,
            font=(S.FONT_FAMILY, S.FONT_SIZE_MD, "bold"),
        ).grid(row=row_i[0], column=0, columnspan=2, sticky="w", pady=(0, 8))
        row_i[0] += 1

        # Cantidad a devolver
        cant_max = item.cantidad
        cant_var = tk.IntVar(value=cant_max)

        _lbl("Cant. a devolver")
        cant_spin = tk.Spinbox(
            body, from_=1, to=cant_max, textvariable=cant_var,
            width=5, font=(S.FONT_FAMILY, S.FONT_SIZE_MD),
            state="readonly" if cant_max == 1 else "normal",
        )
        cant_spin.grid(row=row_i[0], column=1, sticky="w", pady=4)
        row_i[0] += 1

        # ¿Vuelve al stock?
        tiene_variante = item.variante_id is not None
        stock_var = tk.BooleanVar(value=tiene_variante)
        _lbl("¿Vuelve al stock?")
        stock_chk = tk.Checkbutton(
            body, variable=stock_var,
            bg=S.BG, text="Sí, reponer al inventario",
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM),
        )
        if not tiene_variante:
            stock_var.set(False)
            stock_chk.config(state="disabled")
        stock_chk.grid(row=row_i[0], column=1, sticky="w", pady=4)
        row_i[0] += 1

        # Cantidad a reponer (visible si vuelve al stock y qty > 1)
        stock_cant_var = tk.IntVar(value=cant_max)
        stock_cant_row = row_i[0]
        _lbl("Cant. a reponer")
        stock_cant_spin = tk.Spinbox(
            body, from_=1, to=cant_max, textvariable=stock_cant_var,
            width=5, font=(S.FONT_FAMILY, S.FONT_SIZE_MD),
        )
        stock_cant_spin.grid(row=stock_cant_row, column=1, sticky="w", pady=4)
        row_i[0] += 1

        def _toggle_stock_cant(*_):
            if stock_var.get() and cant_max > 1:
                stock_cant_spin.config(state="normal")
                stock_cant_var.set(cant_var.get())
            else:
                stock_cant_spin.config(state="disabled")

        def _sync_stock_max(*_):
            new_max = cant_var.get()
            stock_cant_spin.config(to=new_max)
            stock_cant_var.set(new_max)

        stock_var.trace_add("write", _toggle_stock_cant)
        cant_var.trace_add("write", _sync_stock_max)
        _toggle_stock_cant()

        # Observación
        _lbl("Observación")
        obs_var = tk.StringVar()
        tk.Entry(body, textvariable=obs_var, **S.ENTRY_STYLE, width=24,
                 ).grid(row=row_i[0], column=1, sticky="w", pady=4)
        row_i[0] += 1

        # Fecha
        _lbl("Fecha")
        fecha_entry = DateEntry(
            body, width=14, background=S.PRIMARY, foreground="white",
            borderwidth=2, date_pattern="yyyy-mm-dd",
            font=(S.FONT_FAMILY, S.FONT_SIZE_MD),
        )
        fecha_entry.set_date(date.today())
        fecha_entry.grid(row=row_i[0], column=1, sticky="w", pady=4)
        row_i[0] += 1

        def _confirmar():
            cant = cant_var.get()
            a_stock = stock_cant_var.get() if (stock_var.get() and tiene_variante) else 0
            try:
                dev = devolucion_service.registrar(
                    item=item,
                    cantidad_devuelta=cant,
                    cantidad_a_stock=a_stock,
                    observacion=obs_var.get().strip(),
                    fecha=fecha_entry.get_date().strftime("%Y-%m-%d"),
                )
            except ValueError as exc:
                messagebox.showerror("Error", str(exc), parent=win)
                return
            item.devolucion = dev
            win.destroy()
            self._render_items()
            self._render_balance()
            if self._on_change:
                self._on_change()

        btn_row = tk.Frame(win, bg=S.BG)
        btn_row.pack(fill="x", padx=20, pady=(0, 16))
        tk.Button(btn_row, text="Cancelar", **S.BTN_SECONDARY, command=win.destroy).pack(side="right")
        tk.Button(btn_row, text="Confirmar devolución",
                  bg=S.WARNING, fg="white",
                  font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "bold"),
                  relief="flat", bd=0, padx=10, pady=6, cursor="hand2",
                  command=_confirmar,
                  ).pack(side="right", padx=(0, 8))

        win.update_idletasks()
        ww, wh = win.winfo_width(), win.winfo_height()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"{ww}x{wh}+{(sw-ww)//2}+{(sh-wh)//2}")

    # ── Balance render ────────────────────────────────────────────────────

    def _render_balance(self):
        for w in self._balance_container.winfo_children():
            w.destroy()

        v = self._venta
        f = self._balance_container

        def _balance_row(label, value, fg=S.TEXT_DARK, bold=False):
            row = tk.Frame(f, bg=S.BG)
            row.pack(fill="x", pady=1)
            font_weight = "bold" if bold else "normal"
            tk.Label(row, text=label, bg=S.BG, fg=S.TEXT_MEDIUM,
                     font=(S.FONT_FAMILY, S.FONT_SIZE_SM), anchor="w",
                     ).pack(side="left")
            tk.Label(row, text=value, bg=S.BG, fg=fg,
                     font=(S.FONT_FAMILY, S.FONT_SIZE_SM, font_weight), anchor="e",
                     ).pack(side="right")

        _balance_row("Total venta:", S.fmt_moneda(v.total))

        if v.total_devoluciones > 0:
            _balance_row("Devoluciones:", f"- {S.fmt_moneda(v.total_devoluciones)}", fg=S.DANGER)
            _balance_row("Total ajustado:", S.fmt_moneda(v.total_ajustado), fg=S.PRIMARY_DARK, bold=True)

        tk.Frame(f, bg=S.BORDER, height=1).pack(fill="x", pady=4)
        _balance_row("Total pagado:", S.fmt_moneda(v.total_pagado))

        saldo = v.saldo
        if saldo > 0:
            _balance_row("Saldo pendiente:", S.fmt_moneda(saldo), fg=S.WARNING, bold=True)
        elif saldo < 0:
            _balance_row("Pago en exceso:", f"{S.fmt_moneda(abs(saldo))}  (devolver al cliente)", fg=S.DANGER, bold=True)
        else:
            _balance_row("Saldo:", "$0,00  ✓ Saldado", fg=S.SUCCESS, bold=True)

    # ── Pagos render ──────────────────────────────────────────────────────

    def _render_pagos(self):
        for w in self._pagos_container.winfo_children():
            w.destroy()
        v = self._venta
        if not v.pagos:
            tk.Label(self._pagos_container, text="Sin pagos registrados.",
                     bg=S.BG, fg=S.TEXT_LIGHT,
                     font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "italic"),
                     ).pack(anchor="w")
        for p in v.pagos:
            row = tk.Frame(self._pagos_container, bg=S.BG)
            row.pack(fill="x", pady=1)
            tk.Label(
                row,
                text=f"  #{p.id}   {S.fmt_moneda(p.monto)}   {p.tipo}   {p.fecha}",
                bg=S.BG, fg=S.TEXT_DARK,
                font=(S.FONT_FAMILY, S.FONT_SIZE_SM),
            ).pack(side="left")
            tk.Button(
                row, text="✕",
                bg=S.BG, fg=S.DANGER,
                font=(S.FONT_FAMILY, S.FONT_SIZE_SM),
                relief="flat", bd=0, cursor="hand2",
                command=lambda pid=p.id: self._quitar_pago(pid),
            ).pack(side="left", padx=4)
        self._render_balance()

    def _agregar_pago(self):
        win = tk.Toplevel(self)
        win.title("Nuevo pago")
        win.configure(bg=S.BG)
        win.resizable(False, False)
        win.grab_set()

        body = tk.Frame(win, bg=S.BG, padx=20, pady=16)
        body.pack()
        body.columnconfigure(1, weight=1)

        def _lbl(text, row):
            tk.Label(body, text=text, bg=S.BG, fg=S.TEXT_MEDIUM,
                     font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "bold"), anchor="w",
                     ).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=4)

        _lbl("Monto $", 0)
        monto_var = tk.StringVar()
        monto_frame = tk.Frame(body, bg=S.BG)
        monto_frame.grid(row=0, column=1, sticky="w", pady=4)
        tk.Entry(monto_frame, textvariable=monto_var, **S.ENTRY_STYLE, width=12).pack(side="left")
        saldo_actual = self._venta.saldo
        if saldo_actual > 0:
            tk.Button(
                monto_frame,
                text=f"Pagar saldo ({S.fmt_moneda(saldo_actual)})",
                bg=S.BG_SIDEBAR, fg=S.PRIMARY_DARK,
                font=(S.FONT_FAMILY, S.FONT_SIZE_SM),
                relief="flat", bd=0, padx=8, cursor="hand2",
                command=lambda: monto_var.set(f"{saldo_actual:.2f}"),
            ).pack(side="left", padx=(8, 0))

        _lbl("Tipo", 1)
        tipo_var = tk.StringVar(value="efectivo")
        ttk.Combobox(body, textvariable=tipo_var,
                     values=["efectivo", "transferencia", "tarjeta"],
                     state="readonly", width=16,
                     font=(S.FONT_FAMILY, S.FONT_SIZE_MD),
                     ).grid(row=1, column=1, sticky="w", pady=4)

        _lbl("Fecha", 2)
        fecha_entry = DateEntry(
            body, width=14, background=S.PRIMARY, foreground="white",
            borderwidth=2, date_pattern="yyyy-mm-dd",
            font=(S.FONT_FAMILY, S.FONT_SIZE_MD),
        )
        fecha_entry.set_date(date.today())
        fecha_entry.grid(row=2, column=1, sticky="w", pady=4)

        def _save():
            try:
                monto = float(monto_var.get().replace(",", "."))
            except ValueError:
                messagebox.showerror("Error", "Monto inválido.", parent=win)
                return
            try:
                p = venta_service.agregar_pago(
                    self._venta.id, monto, tipo_var.get(), fecha_entry.get_date().strftime("%Y-%m-%d")
                )
                self._venta.pagos.append(p)
                win.destroy()
                self._render_pagos()
                if self._on_change:
                    self._on_change()
            except ValueError as exc:
                messagebox.showerror("Error", str(exc), parent=win)

        btn_row = tk.Frame(win, bg=S.BG)
        btn_row.pack(fill="x", padx=20, pady=(0, 16))
        tk.Button(btn_row, text="Cancelar", **S.BTN_SECONDARY, command=win.destroy).pack(side="right")
        tk.Button(btn_row, text="Guardar", **S.BTN_PRIMARY, command=_save).pack(side="right", padx=(0, 8))

        win.update_idletasks()
        ww, wh = win.winfo_width(), win.winfo_height()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"{ww}x{wh}+{(sw-ww)//2}+{(sh-wh)//2}")

    def _quitar_pago(self, pago_id: int):
        if not messagebox.askyesno("Eliminar pago", "¿Eliminar este pago?", parent=self):
            return
        venta_service.eliminar_pago(pago_id)
        self._venta.pagos = [p for p in self._venta.pagos if p.id != pago_id]
        self._render_pagos()
        if self._on_change:
            self._on_change()
