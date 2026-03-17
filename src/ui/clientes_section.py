"""
Sección Clientes: listado paginado, buscador, nuevo/editar/eliminar cliente.
"""
import tkinter as tk
from tkinter import ttk, messagebox

from src.models.cliente import Cliente
from src.services.cliente_service import cliente_service
from src.ui import styles as S
from src.ui.cliente_form_modal import ClienteFormModal


PAGE_SIZE = 20

SEXO_LABEL = {"M": "Masculino", "F": "Femenino", "Otro": "Otro", "": "-"}

COLUMNS = [
    ("id",               "ID",               60,  "center"),
    ("cuit_dni",         "CUIT / DNI",       120, "w"),
    ("nombre",           "Nombre",           200, "w"),
    ("telefono",         "Teléfono",         120, "w"),
    ("email",            "Email",            180, "w"),
    ("direccion",        "Dirección",        200, "w"),
    ("fecha_nacimiento", "Nac.",              90, "center"),
    ("sexo",             "Sexo",             80,  "center"),
]


class ClientesSection(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=S.BG, **kwargs)
        self._current_page = 1
        self._total_pages  = 1
        self._search_query = ""
        self._clientes: list[Cliente] = []
        self._build()
        self.refresh()

    # ── Construcción de la UI ─────────────────────────────────────────────

    def _build(self):
        # Cabecera
        header = tk.Frame(self, bg=S.BG, padx=16, pady=12)
        header.pack(fill="x")
        tk.Label(header, text="Clientes", **S.LABEL_TITLE, padx=0).pack(side="left")
        tk.Button(
            header, text="+ Nuevo Cliente",
            **S.BTN_PRIMARY, command=self._open_new_form,
        ).pack(side="right")

        # Buscador
        search_bar = tk.Frame(self, bg=S.BG, padx=16)
        search_bar.pack(fill="x", pady=(0, 8))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search)
        tk.Entry(
            search_bar, textvariable=self.search_var,
            **S.ENTRY_STYLE, width=40,
        ).pack(side="left")
        tk.Label(
            search_bar, text="Buscar por nombre, teléfono, CUIT/DNI o email",
            bg=S.BG, fg=S.TEXT_LIGHT,
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "italic"),
        ).pack(side="left", padx=(10, 0))

        # Tabla
        table_frame = tk.Frame(self, bg=S.BG, padx=16)
        table_frame.pack(fill="both", expand=True)

        style = ttk.Style()
        style.configure(
            "Clientes.Treeview",
            background=S.BG_CARD, rowheight=26,
            font=(S.FONT_FAMILY, S.FONT_SIZE_MD),
            fieldbackground=S.BG_CARD,
        )
        style.configure(
            "Clientes.Treeview.Heading",
            background=S.BG_SIDEBAR, foreground=S.PRIMARY_DARK,
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "bold"),
            relief="flat",
        )
        style.map("Clientes.Treeview", background=[("selected", S.PRIMARY_LIGHT)])

        cols = tuple(c[0] for c in COLUMNS)
        self.tree = ttk.Treeview(
            table_frame, columns=cols, show="headings",
            style="Clientes.Treeview", selectmode="browse",
        )
        for key, heading, width, anchor in COLUMNS:
            self.tree.heading(key, text=heading)
            self.tree.column(key, width=width, anchor=anchor, stretch=(key == "nombre"))

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._on_row_select)

        def _on_double_click(event):
            item = self.tree.identify_row(event.y)
            if item:
                c = cliente_service.obtener_por_id(int(item))
                if c:
                    ClienteFormModal(self, cliente=c, on_save=self.refresh)

        self.tree.bind("<Double-1>", _on_double_click)

        # Panel de acciones + paginación
        bottom = tk.Frame(self, bg=S.BG, padx=16, pady=8)
        bottom.pack(fill="x")

        # Acciones
        action_frame = tk.Frame(bottom, bg=S.BG)
        action_frame.pack(side="left")

        self.lbl_selected = tk.Label(
            action_frame,
            text="Seleccioná un cliente para editarlo o eliminarlo.",
            bg=S.BG, fg=S.TEXT_LIGHT,
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "italic"),
        )
        self.lbl_selected.pack(side="left", padx=(0, 16))

        self.btn_edit = tk.Button(
            action_frame, text="✏ Editar",
            **S.BTN_SUCCESS, command=self._edit_selected, state="disabled",
        )
        self.btn_edit.pack(side="left", padx=(0, 8))

        self.btn_delete = tk.Button(
            action_frame, text="🗑 Eliminar",
            **S.BTN_DANGER, command=self._delete_selected, state="disabled",
        )
        self.btn_delete.pack(side="left")

        # Paginación
        pag_frame = tk.Frame(bottom, bg=S.BG)
        pag_frame.pack(side="right")

        self.btn_prev = tk.Button(
            pag_frame, text="◀",
            **S.BTN_SECONDARY, command=self._prev_page,
        )
        self.btn_prev.pack(side="left")

        self.lbl_page = tk.Label(
            pag_frame, text="",
            bg=S.BG, fg=S.TEXT_MEDIUM,
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM),
        )
        self.lbl_page.pack(side="left", padx=8)

        self.btn_next = tk.Button(
            pag_frame, text="▶",
            **S.BTN_SECONDARY, command=self._next_page,
        )
        self.btn_next.pack(side="left")

    # ── Datos ─────────────────────────────────────────────────────────────

    def _on_search(self, *_):
        self._search_query = self.search_var.get().strip()
        self._current_page = 1
        self._load()

    def refresh(self):
        self._current_page = 1
        self._load()

    def _load(self):
        self._clientes, total = cliente_service.listar_paginado(
            search=self._search_query,
            page=self._current_page,
            page_size=PAGE_SIZE,
        )
        self._total_pages = cliente_service.calcular_total_paginas(total, PAGE_SIZE)
        self._render_table()
        self._deselect()

    def _render_table(self):
        self.tree.delete(*self.tree.get_children())
        sexo_map = {"M": "M", "F": "F", "Otro": "Otro", "": "-"}
        for c in self._clientes:
            self.tree.insert("", "end", iid=str(c.id), values=(
                c.id,
                c.cuit_dni or "-",
                c.nombre,
                c.telefono,
                c.email or "-",
                c.direccion or "-",
                c.fecha_nacimiento or "-",
                sexo_map.get(c.sexo, "-"),
            ))
        self.lbl_page.config(
            text=f"Página {self._current_page} / {self._total_pages}"
        )
        self.btn_prev.config(state="normal" if self._current_page > 1 else "disabled")
        self.btn_next.config(state="normal" if self._current_page < self._total_pages else "disabled")

    # ── Paginación ────────────────────────────────────────────────────────

    def _prev_page(self):
        if self._current_page > 1:
            self._current_page -= 1
            self._load()

    def _next_page(self):
        if self._current_page < self._total_pages:
            self._current_page += 1
            self._load()

    # ── Selección y acciones ──────────────────────────────────────────────

    def _on_row_select(self, event=None):
        selected = self.tree.selection()
        if selected:
            c = cliente_service.obtener_por_id(int(selected[0]))
            if c:
                self.lbl_selected.config(
                    text=f"Seleccionado: {c.nombre}  ({c.telefono})",
                    fg=S.TEXT_DARK,
                )
                self.btn_edit.config(state="normal")
                self.btn_delete.config(state="normal")

    def _deselect(self):
        self.tree.selection_remove(self.tree.selection())
        self.lbl_selected.config(
            text="Seleccioná un cliente para editarlo o eliminarlo.",
            fg=S.TEXT_LIGHT,
        )
        self.btn_edit.config(state="disabled")
        self.btn_delete.config(state="disabled")

    def _get_selected(self) -> Cliente | None:
        selected = self.tree.selection()
        if not selected:
            return None
        return cliente_service.obtener_por_id(int(selected[0]))

    def _open_new_form(self):
        ClienteFormModal(self, cliente=None, on_save=self.refresh)

    def _edit_selected(self):
        c = self._get_selected()
        if c:
            ClienteFormModal(self, cliente=c, on_save=self.refresh)

    def _delete_selected(self):
        c = self._get_selected()
        if not c:
            return
        if messagebox.askyesno(
            "Confirmar eliminación",
            f"Eliminar '{c.nombre}'?\nEsta acción no se puede deshacer.",
            parent=self,
        ):
            cliente_service.eliminar(c.id)
            self.refresh()
