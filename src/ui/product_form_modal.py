"""
Modal formulario para crear / editar un producto.
Gestiona variantes (talla + color + stock) y múltiples imágenes.
"""
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Callable

from src.models.producto import Producto, ProductoImagen
from src.services.producto_service import producto_service
from src.ui import widgets as W
from src.ui import styles as S


class ProductFormModal(tk.Toplevel):
    def __init__(
        self,
        parent,
        product: Producto | None = None,
        on_save: Callable | None = None,
    ):
        super().__init__(parent)
        self.product = product
        self.on_save = on_save
        # variantes editables: lista de dicts {id, talla, color, stock}
        self._variantes: list[dict] = []
        # imágenes existentes a conservar (ProductoImagen con id)
        self._imagenes_existentes: list[ProductoImagen] = []
        # rutas locales de nuevas imágenes seleccionadas
        self._nuevas_src: list[str] = []
        # refs PhotoImage para evitar garbage collection
        self._photos: list = []

        self.title("Editar Producto" if product else "Nuevo Producto")
        self.configure(bg=S.BG)
        self.resizable(True, True)
        self.minsize(560, 680)

        self._build()
        self._populate()
        self._center()
        self.grab_set()

    def _center(self):
        self.update_idletasks()
        w = max(self.winfo_width(), 580)
        h = max(self.winfo_height(), 680)
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w)//2}+{(sh - h)//2}")

    # ── Construcción de la UI ────────────────────────────────────────────

    def _build(self):
        header = tk.Frame(self, bg=S.PRIMARY, padx=20, pady=10)
        header.pack(fill="x")
        tk.Label(
            header,
            text="Editar Producto" if self.product else "Nuevo Producto",
            bg=S.PRIMARY, fg="white",
            font=(S.FONT_FAMILY, S.FONT_SIZE_LG, "bold"),
        ).pack(side="left")

        outer, _, self.body = W.make_scrollable_frame(self, bg=S.BG)
        outer.pack(fill="both", expand=True, padx=16, pady=10)
        self.body.columnconfigure(1, weight=1)

        row = 0

        def _entry(parent):
            return tk.Entry(parent, **S.ENTRY_STYLE)

        def _add_field(label, factory, r):
            tk.Label(
                self.body, text=label + ":",
                bg=S.BG, fg=S.TEXT_MEDIUM,
                font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "bold"),
                anchor="e",
            ).grid(row=r, column=0, sticky="e", padx=(0, 10), pady=5)
            w = factory(self.body)
            w.grid(row=r, column=1, sticky="ew", pady=5, padx=(0, 4))
            return w

        self.e_codigo    = _add_field("Código *",            _entry, row); row += 1
        self.e_nombre    = _add_field("Nombre *",            _entry, row); row += 1

        # Descripción (Text multilinea)
        tk.Label(
            self.body, text="Descripción:",
            bg=S.BG, fg=S.TEXT_MEDIUM,
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "bold"), anchor="e",
        ).grid(row=row, column=0, sticky="ne", padx=(0, 10), pady=5)
        self.e_descripcion = tk.Text(
            self.body, height=3,
            bg="white", fg=S.TEXT_DARK,
            font=(S.FONT_FAMILY, S.FONT_SIZE_MD),
            relief="solid", bd=1,
        )
        self.e_descripcion.grid(row=row, column=1, sticky="ew", pady=5, padx=(0, 4))
        row += 1

        self.e_categoria = _add_field("Categoría",           _entry, row); row += 1
        self.e_costo     = _add_field("Precio de costo ($)", _entry, row); row += 1
        self.e_ganancia  = _add_field("% Ganancia",          _entry, row); row += 1

        self.e_costo.bind("<KeyRelease>",    self._calc_precio)
        self.e_ganancia.bind("<KeyRelease>", self._calc_precio)

        # Precio unitario (calculado, solo lectura)
        tk.Label(
            self.body, text="Precio unitario ($):",
            bg=S.BG, fg=S.TEXT_MEDIUM,
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "bold"), anchor="e",
        ).grid(row=row, column=0, sticky="e", padx=(0, 10), pady=5)
        self.e_precio = tk.Entry(
            self.body,
            font=(S.FONT_FAMILY, S.FONT_SIZE_MD),
            state="disabled", relief="solid", bd=1,
            disabledbackground="#f0f0f0",
            disabledforeground=S.TEXT_DARK,
        )
        self.e_precio.grid(row=row, column=1, sticky="ew", pady=5, padx=(0, 4))
        row += 1

        # ── Sección Variantes ──────────────────────────────────────────
        tk.Label(
            self.body, text="Variantes (talla / color / stock)",
            bg=S.BG, fg=S.PRIMARY_DARK,
            font=(S.FONT_FAMILY, S.FONT_SIZE_MD, "bold"),
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=(0, 4), pady=(14, 4))
        row += 1

        variantes_frame = tk.Frame(self.body, bg=S.BG)
        variantes_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        row += 1
        self._build_variantes_section(variantes_frame)

        # ── Sección Imágenes ───────────────────────────────────────────
        tk.Label(
            self.body, text="Imágenes",
            bg=S.BG, fg=S.PRIMARY_DARK,
            font=(S.FONT_FAMILY, S.FONT_SIZE_MD, "bold"),
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=(0, 4), pady=(14, 4))
        row += 1

        self._imagenes_container = tk.Frame(self.body, bg=S.BG)
        self._imagenes_container.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self._refresh_imagenes_ui()

        # Botones footer
        btn_frame = tk.Frame(self, bg=S.BG)
        btn_frame.pack(fill="x", padx=16, pady=(0, 14))
        tk.Button(btn_frame, text="Guardar",  **S.BTN_PRIMARY,   command=self._save).pack(side="right", padx=(8, 0))
        tk.Button(btn_frame, text="Cancelar", **S.BTN_SECONDARY, command=self.destroy).pack(side="right")

    # ── Sección Variantes ────────────────────────────────────────────────

    def _build_variantes_section(self, parent: tk.Frame):
        # Cabecera de columnas
        header = tk.Frame(parent, bg=S.BG_SIDEBAR)
        header.pack(fill="x")
        for text, w in [("Talla", 13), ("Color", 16), ("Stock", 9)]:
            tk.Label(
                header, text=text,
                bg=S.BG_SIDEBAR, fg=S.TEXT_DARK,
                font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "bold"),
                width=w, anchor="w",
            ).pack(side="left", padx=(4, 0), pady=3)

        # Contenedor de filas
        self._variantes_rows_frame = tk.Frame(parent, bg=S.BG)
        self._variantes_rows_frame.pack(fill="x")
        self._refresh_variantes_ui()

        tk.Button(
            parent, text="+ Agregar variante",
            **S.BTN_SECONDARY, command=self._add_variante_row,
        ).pack(anchor="w", pady=(6, 0))

    def _refresh_variantes_ui(self):
        for w in self._variantes_rows_frame.winfo_children():
            w.destroy()
        for i, v in enumerate(self._variantes):
            self._make_variante_row(self._variantes_rows_frame, i, v)

    def _make_variante_row(self, parent: tk.Frame, idx: int, v: dict):
        row = tk.Frame(parent, bg=S.BG, pady=2)
        row.pack(fill="x")

        e_talla = tk.Entry(row, font=(S.FONT_FAMILY, S.FONT_SIZE_MD), relief="solid", bd=1, width=13)
        e_talla.insert(0, v.get("talla", ""))
        e_talla.pack(side="left", padx=(0, 4))
        e_talla.bind("<KeyRelease>", lambda e, i=idx: self._sync_variante(i, "talla", e.widget.get()))

        e_color = tk.Entry(row, font=(S.FONT_FAMILY, S.FONT_SIZE_MD), relief="solid", bd=1, width=16)
        e_color.insert(0, v.get("color", ""))
        e_color.pack(side="left", padx=(0, 4))
        e_color.bind("<KeyRelease>", lambda e, i=idx: self._sync_variante(i, "color", e.widget.get()))

        e_stock = tk.Entry(row, font=(S.FONT_FAMILY, S.FONT_SIZE_MD), relief="solid", bd=1, width=9)
        e_stock.insert(0, str(v.get("stock", 0)))
        e_stock.pack(side="left", padx=(0, 4))
        e_stock.bind("<KeyRelease>", lambda e, i=idx: self._sync_variante(i, "stock", e.widget.get()))

        tk.Button(
            row, text="✕",
            bg="#FFCDD2", fg="#B71C1C",
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "bold"),
            relief="flat", bd=0, padx=6, pady=2, cursor="hand2",
            command=lambda i=idx: self._remove_variante(i),
        ).pack(side="left")

    def _sync_variante(self, idx: int, key: str, value: str):
        if idx < len(self._variantes):
            self._variantes[idx][key] = value

    def _add_variante_row(self):
        self._variantes.append({"id": None, "talla": "", "color": "", "stock": 0})
        self._refresh_variantes_ui()

    def _remove_variante(self, idx: int):
        self._variantes.pop(idx)
        self._refresh_variantes_ui()

    # ── Sección Imágenes ─────────────────────────────────────────────────

    def _refresh_imagenes_ui(self):
        for w in self._imagenes_container.winfo_children():
            w.destroy()
        self._photos.clear()

        strip = tk.Frame(self._imagenes_container, bg=S.BG)
        strip.pack(fill="x")

        for img in self._imagenes_existentes:
            path = producto_service.get_image_path(img.filename)
            self._make_image_thumb(
                strip, path,
                on_remove=lambda fi=img: self._remove_existente(fi),
            )

        for i, src in enumerate(self._nuevas_src):
            self._make_image_thumb(
                strip, src,
                on_remove=lambda idx=i: self._remove_nueva(idx),
            )

        tk.Button(
            self._imagenes_container, text="+ Agregar imagen",
            **S.BTN_SECONDARY, command=self._add_image,
        ).pack(anchor="w", pady=(6, 0))

    def _make_image_thumb(self, parent: tk.Frame, path: str, on_remove: Callable):
        frame = tk.Frame(parent, bg=S.BG_SIDEBAR, relief="solid", bd=1)
        frame.pack(side="left", padx=4, pady=2)

        photo = W.load_thumbnail(path, size=(80, 80)) if path else None
        if photo:
            self._photos.append(photo)
            tk.Label(frame, image=photo, bg=S.BG_SIDEBAR).pack()
        else:
            tk.Label(
                frame, text="📷", bg=S.BG_SIDEBAR, fg=S.TEXT_LIGHT,
                font=(S.FONT_FAMILY, 22), width=6, height=3,
            ).pack()

        tk.Button(
            frame, text="✕ Quitar",
            bg="#FFCDD2", fg="#B71C1C",
            font=(S.FONT_FAMILY, 8), relief="flat", bd=0,
            padx=4, pady=1, cursor="hand2",
            command=on_remove,
        ).pack(fill="x")

    def _add_image(self):
        path = filedialog.askopenfilename(
            title="Seleccionar imagen",
            filetypes=[
                ("Imágenes", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"),
                ("Todos",    "*.*"),
            ],
        )
        if path:
            self._nuevas_src.append(path)
            self._refresh_imagenes_ui()

    def _remove_existente(self, img: ProductoImagen):
        self._imagenes_existentes = [i for i in self._imagenes_existentes if i is not img]
        self._refresh_imagenes_ui()

    def _remove_nueva(self, idx: int):
        if idx < len(self._nuevas_src):
            self._nuevas_src.pop(idx)
        self._refresh_imagenes_ui()

    # ── Población de datos ───────────────────────────────────────────────

    def _populate(self):
        if not self.product:
            return
        p = self.product

        def _set(widget, value):
            widget.delete(0, tk.END)
            widget.insert(0, str(value) if value is not None else "")

        _set(self.e_codigo,    p.codigo)
        _set(self.e_nombre,    p.nombre)
        self.e_descripcion.delete("1.0", tk.END)
        self.e_descripcion.insert("1.0", p.descripcion)
        _set(self.e_categoria, p.categoria)
        _set(self.e_costo,     p.precio_costo)
        _set(self.e_ganancia,  p.porcentaje_ganancia)
        self._set_precio(p.precio_unitario)

        self._variantes = [
            {"id": v.id, "talla": v.talla, "color": v.color, "stock": v.stock}
            for v in p.variantes
        ]
        self._imagenes_existentes = list(p.imagenes)
        self._refresh_variantes_ui()
        self._refresh_imagenes_ui()

    # ── Helpers de UI ────────────────────────────────────────────────────

    def _calc_precio(self, event=None):
        try:
            costo  = float(self.e_costo.get().replace(",", "."))
            pct    = float(self.e_ganancia.get().replace(",", "."))
            self._set_precio(costo + costo * pct / 100)
        except ValueError:
            self._set_precio(0)

    def _set_precio(self, value):
        self.e_precio.config(state="normal")
        self.e_precio.delete(0, tk.END)
        self.e_precio.insert(0, f"{float(value):.2f}")
        self.e_precio.config(state="disabled")

    # ── Guardar ──────────────────────────────────────────────────────────

    def _validate(self) -> bool:
        if not self.e_codigo.get().strip():
            messagebox.showwarning("Validación", "El código es obligatorio.", parent=self)
            return False
        if not self.e_nombre.get().strip():
            messagebox.showwarning("Validación", "El nombre es obligatorio.", parent=self)
            return False
        try:
            float(self.e_costo.get().replace(",", "."))
            float(self.e_ganancia.get().replace(",", "."))
        except ValueError:
            messagebox.showwarning(
                "Validación", "Precio de costo y % ganancia deben ser números.", parent=self
            )
            return False
        for v in self._variantes:
            try:
                int(v.get("stock", 0))
            except (ValueError, TypeError):
                messagebox.showwarning(
                    "Validación", "El stock de cada variante debe ser un número entero.", parent=self
                )
                return False
        return True

    def _save(self):
        if not self._validate():
            return

        data = {
            "codigo":              self.e_codigo.get().strip(),
            "nombre":              self.e_nombre.get().strip(),
            "descripcion":         self.e_descripcion.get("1.0", tk.END).strip(),
            "categoria":           self.e_categoria.get().strip(),
            "precio_costo":        float(self.e_costo.get().replace(",", ".")),
            "porcentaje_ganancia": float(self.e_ganancia.get().replace(",", ".")),
        }

        try:
            if self.product:
                producto_service.actualizar(
                    self.product.id,
                    data,
                    variantes=self._variantes,
                    imagenes_src=self._nuevas_src,
                    imagenes_existentes=self._imagenes_existentes,
                )
            else:
                producto_service.crear(
                    data,
                    variantes=self._variantes,
                    imagenes_src=self._nuevas_src,
                )
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo guardar:\n{exc}", parent=self)
            return

        self.destroy()
        if self.on_save:
            self.on_save()
