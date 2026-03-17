"""
Sección Historial de Ventas.
Listado paginado con búsqueda por cliente y filtros de fecha (día/mes/año).
Doble clic abre VentaDetailModal.
"""
import tkinter as tk
from tkinter import ttk
from datetime import date

from src.models.venta import Venta
from src.services.venta_service import venta_service
from src.ui import styles as S
from src.ui.venta_detail_modal import VentaDetailModal


PAGE_SIZE = 25

COLUMNS = [
    ("nro",      "# Venta",    70,  "center"),
    ("cliente",  "Cliente",   200,  "w"),
    ("fecha",    "Fecha",     130,  "center"),
    ("total",    "Total",      90,  "e"),
    ("pagado",   "Pagado",     90,  "e"),
    ("saldo",    "Saldo",      90,  "e"),
]


class HistorialVentasSection(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=S.BG, **kwargs)
        self._current_page = 1
        self._total_pages  = 1
        self._search   = ""
        self._f_desde  = ""
        self._f_hasta  = ""
        self._ventas: list[Venta] = []
        self._build()
        self.refresh()

    # ── Build ─────────────────────────────────────────────────────────────

    def _build(self):
        # Cabecera
        header = tk.Frame(self, bg=S.BG, padx=16, pady=10)
        header.pack(fill="x")
        tk.Label(header, text="Historial de Ventas", **S.LABEL_TITLE, padx=0).pack(side="left")

        # Barra de filtros
        filters = tk.Frame(self, bg=S.BG, padx=16)
        filters.pack(fill="x", pady=(0, 6))

        # Búsqueda por cliente
        tk.Label(filters, text="Cliente:", bg=S.BG, fg=S.TEXT_MEDIUM,
                 font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 6))
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_filter_change)
        tk.Entry(filters, textvariable=self._search_var, **S.ENTRY_STYLE, width=24,
                 ).grid(row=0, column=1, sticky="w", padx=(0, 20))

        # Filtro Desde
        tk.Label(filters, text="Desde:", bg=S.BG, fg=S.TEXT_MEDIUM,
                 font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "bold")).grid(row=0, column=2, sticky="w", padx=(0, 6))
        self._desde_var = tk.StringVar()
        self._desde_var.trace_add("write", self._on_filter_change)
        tk.Entry(filters, textvariable=self._desde_var, **S.ENTRY_STYLE, width=12,
                 ).grid(row=0, column=3, sticky="w", padx=(0, 4))
        tk.Label(filters, text="AAAA-MM-DD", bg=S.BG, fg=S.TEXT_LIGHT,
                 font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "italic")).grid(row=0, column=4, sticky="w", padx=(0, 16))

        # Filtro Hasta
        tk.Label(filters, text="Hasta:", bg=S.BG, fg=S.TEXT_MEDIUM,
                 font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "bold")).grid(row=0, column=5, sticky="w", padx=(0, 6))
        self._hasta_var = tk.StringVar()
        self._hasta_var.trace_add("write", self._on_filter_change)
        tk.Entry(filters, textvariable=self._hasta_var, **S.ENTRY_STYLE, width=12,
                 ).grid(row=0, column=6, sticky="w", padx=(0, 4))
        tk.Label(filters, text="AAAA-MM-DD", bg=S.BG, fg=S.TEXT_LIGHT,
                 font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "italic")).grid(row=0, column=7, sticky="w", padx=(0, 16))

        # Atajos de fecha
        atajos = tk.Frame(filters, bg=S.BG)
        atajos.grid(row=0, column=8, sticky="w")
        for label, cmd in [
            ("Hoy",       self._filtro_hoy),
            ("Este mes",  self._filtro_mes),
            ("Este año",  self._filtro_anio),
            ("Limpiar",   self._filtro_limpiar),
        ]:
            tk.Button(
                atajos, text=label,
                bg=S.BG_SIDEBAR, fg=S.PRIMARY_DARK,
                font=(S.FONT_FAMILY, S.FONT_SIZE_SM),
                relief="flat", bd=0, padx=8, pady=3, cursor="hand2",
                command=cmd,
            ).pack(side="left", padx=2)

        # Tabla
        table_frame = tk.Frame(self, bg=S.BG, padx=16)
        table_frame.pack(fill="both", expand=True)

        style = ttk.Style()
        style.configure("Hist.Treeview", rowheight=26, font=(S.FONT_FAMILY, S.FONT_SIZE_MD),
                         background=S.BG_CARD, fieldbackground=S.BG_CARD)
        style.configure("Hist.Treeview.Heading", background=S.BG_SIDEBAR, foreground=S.PRIMARY_DARK,
                         font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "bold"), relief="flat")
        style.map("Hist.Treeview", background=[("selected", S.PRIMARY_LIGHT)])

        cols = tuple(c[0] for c in COLUMNS)
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings",
                                  style="Hist.Treeview", selectmode="browse")
        for key, heading, width, anchor in COLUMNS:
            self.tree.heading(key, text=heading)
            self.tree.column(key, width=width, anchor=anchor, stretch=(key == "cliente"))

        sb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", self._on_double_click)

        # Resumen + paginación
        bottom = tk.Frame(self, bg=S.BG, padx=16, pady=8)
        bottom.pack(fill="x")

        self._resumen_var = tk.StringVar()
        tk.Label(bottom, textvariable=self._resumen_var, bg=S.BG, fg=S.TEXT_MEDIUM,
                 font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "italic")).pack(side="left")

        pag = tk.Frame(bottom, bg=S.BG)
        pag.pack(side="right")
        self.btn_prev = tk.Button(pag, text="◀", **S.BTN_SECONDARY, command=self._prev_page)
        self.btn_prev.pack(side="left")
        self.lbl_page = tk.Label(pag, text="", bg=S.BG, fg=S.TEXT_MEDIUM,
                                  font=(S.FONT_FAMILY, S.FONT_SIZE_SM))
        self.lbl_page.pack(side="left", padx=8)
        self.btn_next = tk.Button(pag, text="▶", **S.BTN_SECONDARY, command=self._next_page)
        self.btn_next.pack(side="left")

    # ── Datos ─────────────────────────────────────────────────────────────

    def refresh(self):
        self._current_page = 1
        self._load()

    def _on_filter_change(self, *_):
        self._search  = self._search_var.get().strip()
        self._f_desde = self._desde_var.get().strip()
        self._f_hasta = self._hasta_var.get().strip()
        self._current_page = 1
        self._load()

    def _load(self):
        self._ventas, total = venta_service.listar_historial(
            search=self._search,
            fecha_desde=self._f_desde,
            fecha_hasta=self._f_hasta,
            page=self._current_page,
            page_size=PAGE_SIZE,
        )
        self._total_pages = venta_service.calcular_total_paginas(total, PAGE_SIZE)
        self._render()

    def _render(self):
        self.tree.delete(*self.tree.get_children())
        total_ventas = sum(v.total for v in self._ventas)
        total_pagado = sum(v.total_pagado for v in self._ventas)
        for v in self._ventas:
            saldo_color_tag = "saldo_ok" if v.saldo <= 0 else "saldo_pend"
            self.tree.insert("", "end", iid=str(v.id), values=(
                v.id,
                v.nombre_cliente or "-",
                (v.fecha_apertura or "")[:10],
                S.fmt_moneda(v.total),
                S.fmt_moneda(v.total_pagado),
                S.fmt_moneda(v.saldo),
            ), tags=(saldo_color_tag,))
        self.tree.tag_configure("saldo_ok",   foreground=S.SUCCESS)
        self.tree.tag_configure("saldo_pend", foreground=S.WARNING)
        self.lbl_page.config(text=f"Pág. {self._current_page} / {self._total_pages}")
        self.btn_prev.config(state="normal" if self._current_page > 1 else "disabled")
        self.btn_next.config(state="normal" if self._current_page < self._total_pages else "disabled")
        self._resumen_var.set(
            f"{len(self._ventas)} venta(s)  |  "
            f"Total: {S.fmt_moneda(total_ventas)}  |  Pagado: {S.fmt_moneda(total_pagado)}"
        )

    # ── Paginación ────────────────────────────────────────────────────────

    def _prev_page(self):
        if self._current_page > 1:
            self._current_page -= 1
            self._load()

    def _next_page(self):
        if self._current_page < self._total_pages:
            self._current_page += 1
            self._load()

    # ── Detalle ───────────────────────────────────────────────────────────

    def _on_double_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        venta = venta_service.obtener_por_id(int(item))
        if venta:
            VentaDetailModal(self, venta, on_change=self._load)

    # ── Atajos de fecha ───────────────────────────────────────────────────

    def _filtro_hoy(self):
        hoy = str(date.today())
        self._desde_var.set(hoy)
        self._hasta_var.set(hoy)

    def _filtro_mes(self):
        hoy = date.today()
        self._desde_var.set(f"{hoy.year:04d}-{hoy.month:02d}-01")
        self._hasta_var.set(str(hoy))

    def _filtro_anio(self):
        hoy = date.today()
        self._desde_var.set(f"{hoy.year:04d}-01-01")
        self._hasta_var.set(str(hoy))

    def _filtro_limpiar(self):
        self._search_var.set("")
        self._desde_var.set("")
        self._hasta_var.set("")
