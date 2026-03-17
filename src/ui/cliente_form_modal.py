"""
Modal para crear / editar un cliente.
Campos obligatorios: nombre, telefono.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry

from src.models.cliente import Cliente
from src.services.cliente_service import cliente_service
from src.ui import styles as S


class ClienteFormModal(tk.Toplevel):
    def __init__(self, parent, cliente: Cliente | None = None, on_save=None):
        super().__init__(parent)
        self.title("Nuevo Cliente" if cliente is None else "Editar Cliente")
        self.configure(bg=S.BG)
        self.resizable(False, False)
        self._cliente = cliente
        self._on_save = on_save
        self._build()
        self._center()
        if cliente:
            self._populate()
        self.grab_set()
        self.e_nombre.focus_set()

    # ── Layout ────────────────────────────────────────────────────────────

    def _build(self):
        # Header
        header = tk.Frame(self, bg=S.PRIMARY, padx=20, pady=12)
        header.pack(fill="x")
        title = "Nuevo Cliente" if self._cliente is None else "Editar Cliente"
        tk.Label(
            header, text=title,
            bg=S.PRIMARY, fg="white",
            font=(S.FONT_FAMILY, S.FONT_SIZE_LG, "bold"),
        ).pack(side="left")

        # Body
        body = tk.Frame(self, bg=S.BG, padx=24, pady=16)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)

        def _label(text, row, req=False):
            txt = text + (" *" if req else "")
            tk.Label(
                body, text=txt,
                bg=S.BG, fg=S.TEXT_MEDIUM if not req else S.TEXT_DARK,
                font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "bold"), anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=(0, 14), pady=(6, 2))

        def _entry(row) -> tk.Entry:
            e = tk.Entry(body, **S.ENTRY_STYLE, width=32)
            e.grid(row=row, column=1, sticky="ew", pady=(6, 2))
            return e

        _label("Nombre",           0, req=True)
        self.e_nombre = _entry(0)

        _label("Teléfono",         1, req=True)
        self.e_telefono = _entry(1)

        _label("CUIT / DNI",       2)
        self.e_cuit_dni = _entry(2)

        _label("Email",            3)
        self.e_email = _entry(3)

        _label("Dirección",        4)
        self.e_direccion = _entry(4)

        _label("Fecha nacimiento", 5)
        fecha_frame = tk.Frame(body, bg=S.BG)
        fecha_frame.grid(row=5, column=1, sticky="w", pady=(6, 2))
        self.e_fecha = DateEntry(
            fecha_frame,
            date_pattern="yyyy-mm-dd",
            background=S.PRIMARY, foreground="white",
            borderwidth=1, relief="solid",
            font=(S.FONT_FAMILY, S.FONT_SIZE_MD),
            width=14,
            showweeknumbers=False,
        )
        self.e_fecha.pack(side="left")
        # Empezar sin fecha seleccionada
        self.e_fecha.delete(0, tk.END)

        _label("Sexo",             6)
        self._sexo_var = tk.StringVar(value="")
        sexo_cb = ttk.Combobox(
            body, textvariable=self._sexo_var,
            values=["Sin especificar", "Masculino", "Femenino", "Otro"],
            state="readonly", width=18,
            font=(S.FONT_FAMILY, S.FONT_SIZE_MD),
        )
        sexo_cb.grid(row=6, column=1, sticky="w", pady=(6, 2))
        sexo_cb.set("Sin especificar")

        tk.Label(
            body, text="* campos obligatorios",
            bg=S.BG, fg=S.TEXT_LIGHT,
            font=(S.FONT_FAMILY, S.FONT_SIZE_SM, "italic"),
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=(12, 0))

        # Footer
        btn_frame = tk.Frame(self, bg=S.BG)
        btn_frame.pack(fill="x", padx=24, pady=(4, 16))
        tk.Button(
            btn_frame, text="Cancelar",
            **S.BTN_SECONDARY, command=self.destroy,
        ).pack(side="right")
        tk.Button(
            btn_frame, text="Guardar",
            **S.BTN_PRIMARY, command=self._save,
        ).pack(side="right", padx=(0, 8))

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w)//2}+{(sh - h)//2}")

    # ── Datos ─────────────────────────────────────────────────────────────

    def _populate(self):
        c = self._cliente
        self.e_nombre.insert(0, c.nombre)
        self.e_telefono.insert(0, c.telefono)
        self.e_cuit_dni.insert(0, c.cuit_dni)
        self.e_email.insert(0, c.email)
        self.e_direccion.insert(0, c.direccion)
        if c.fecha_nacimiento:
            try:
                self.e_fecha.set_date(c.fecha_nacimiento)
            except Exception:
                self.e_fecha.delete(0, tk.END)
                self.e_fecha.insert(0, c.fecha_nacimiento)
        _sexo_map = {"M": "Masculino", "F": "Femenino", "Otro": "Otro"}
        self._sexo_var.set(_sexo_map.get(c.sexo, "Sin especificar"))

    def _collect(self) -> dict:
        _sexo_map = {"Masculino": "M", "Femenino": "F", "Otro": "Otro", "Sin especificar": ""}
        fecha = self.e_fecha.get().strip()
        return {
            "nombre":           self.e_nombre.get(),
            "telefono":         self.e_telefono.get(),
            "cuit_dni":         self.e_cuit_dni.get(),
            "email":            self.e_email.get(),
            "direccion":        self.e_direccion.get(),
            "fecha_nacimiento": fecha,
            "sexo":             _sexo_map.get(self._sexo_var.get(), ""),
        }

    def _save(self):
        data = self._collect()
        try:
            if self._cliente is None:
                new_id = cliente_service.crear(data)
                saved  = cliente_service.obtener_por_id(new_id)
            else:
                cliente_service.actualizar(self._cliente.id, data)
                saved = cliente_service.obtener_por_id(self._cliente.id)
        except ValueError as exc:
            messagebox.showerror("Error de validación", str(exc), parent=self)
            return
        except Exception as exc:
            messagebox.showerror("No se pudo guardar", str(exc), parent=self)
            return

        if self._on_save:
            import inspect
            try:
                sig = inspect.signature(self._on_save)
                if len(sig.parameters) >= 1:
                    self._on_save(saved)
                else:
                    self._on_save()
            except (TypeError, ValueError):
                self._on_save()
        self.destroy()
