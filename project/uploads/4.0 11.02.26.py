# -*- coding: utf-8 -*-
"""
Aplicación Tkinter de pluma gaussiana (Versión 4.0 – UI/UX mejorada):
Mejoras respecto a v3.1:
  - Botón "Calcular" prominente + recálculo automático con Enter / FocusOut en entries
  - Panel de Resultados fijo (fuera del scroll), siempre visible
  - Advertencia visible cuando "Dominante (serie)" no tiene datos cargados
  - Campos Briggs se deshabilitan automáticamente cuando el checkbox está desactivado
  - Cursor de espera (watch) durante el cálculo
  - Botones de exportación agrupados en sección propia
  - Ventana Info cierra con Escape y tiene botón Cerrar visible
  - Consistencia tipográfica en labels
  - Validación en tiempo real de entries (borde rojo / verde)
  - Hint en frecuencias manuales (porcentaje o valor relativo)
  - Tabla de frecuencias inicializada con clase seleccionada
  - Popup de cálculo puntual ampliado y con más espacio para resultado
"""

from __future__ import annotations
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import matplotlib

matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import csv

# ============================
# 0) PARÁMETROS DE VIENTO (LEY EXPONENCIAL)
# ============================

WIND_EXPONENT_P = {
    'A': 0.15,
    'B': 0.15,
    'C': 0.20,
    'D': 0.25,
    'E': 0.40,
    'F': 0.60
}


def viento_corregido_exponencial(u10_ms: float, z_m: float, clase_estabilidad: str) -> float:
    clase = (clase_estabilidad or 'D').upper()
    p = float(WIND_EXPONENT_P.get(clase, 0.25))
    z_use = max(float(z_m), 1.0)
    u = float(u10_ms) * (z_use / 10.0) ** p
    return max(u, 0.10)


# ============================
# 1) MÓDULO DE ESTABILIDADES
# ============================

class StabilityModule:
    PG_CLASSES = np.array(list("ABCDEF"))

    @staticmethod
    def classify_pg(es_dia: bool, v: float, G: float | None = None, n_oktas: int | None = None) -> str:
        v = max(float(v), 0.01)

        if es_dia:
            if G is None:
                insol = "M"
            elif G >= 700:
                insol = "F"
            elif G >= 350:
                insol = "M"
            else:
                insol = "D"

            if v <= 2:
                return {"F": "A", "M": "A", "D": "B"}[insol]
            elif v <= 3:
                return {"F": "A", "M": "B", "D": "C"}[insol]
            elif v <= 5:
                return {"F": "B", "M": "C", "D": "D"}[insol]
            elif v <= 6:
                return {"F": "C", "M": "C", "D": "D"}[insol]
            else:
                return {"F": "C", "M": "D", "D": "D"}[insol]

        if n_oktas is None:
            n_oktas = 4

        if n_oktas >= 6:
            return "E" if v <= 3 else "D"
        elif n_oktas >= 3:
            return "E" if v <= 2 else "D"
        else:
            if v <= 2:
                return "F"
            elif v <= 3:
                return "E"
            else:
                return "D"

    @classmethod
    def series_pg(cls, es_dia, v, G=None, n_oktas=None) -> np.ndarray:
        es_dia = np.asarray(list(es_dia), dtype=bool)
        v = np.asarray(list(v), dtype=float)
        N = len(v)
        if G is None:
            G = [None] * N
        if n_oktas is None:
            n_oktas = [None] * N
        clases = [cls.classify_pg(bool(es_dia[i]), float(v[i]), G[i], n_oktas[i]) for i in range(N)]
        return np.array(clases, dtype='<U1')

    @staticmethod
    def frecuencias(clases: np.ndarray) -> dict[str, float]:
        counts = {c: float(np.sum(clases == c)) for c in "ABCDEF"}
        total = sum(counts.values()) or 1.0
        return {k: v / total for k, v in counts.items()}


# ============================
# 2) MÓDULO DE DISPERSIÓN
# ============================

class DispersionModule:
    @staticmethod
    def sigmas(x: np.ndarray, clase_estabilidad: str):
        x = np.asarray(x, dtype=float)
        x = np.maximum(x, 0.001)

        clase = (clase_estabilidad or 'D').upper()
        map_cls = {'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6}
        cat = map_cls.get(clase, 4)

        if cat == 1:
            sigma_y = 0.22 * x * (1 + 0.0001 * x) ** (-0.5)
            sigma_z = 0.20 * x
        elif cat == 2:
            sigma_y = 0.16 * x * (1 + 0.0001 * x) ** (-0.5)
            sigma_z = 0.12 * x
        elif cat == 3:
            sigma_y = 0.11 * x * (1 + 0.0001 * x) ** (-0.5)
            sigma_z = 0.08 * x * (1 + 0.0002 * x) ** (-0.5)
        elif cat == 4:
            sigma_y = 0.08 * x * (1 + 0.0001 * x) ** (-0.5)
            sigma_z = 0.06 * x * (1 + 0.0015 * x) ** (-0.5)
        elif cat == 5:
            sigma_y = 0.06 * x * (1 + 0.0001 * x) ** (-0.5)
            sigma_z = 0.03 * x * (1 + 0.0003 * x) ** (-1.0)
        elif cat == 6:
            sigma_y = 0.04 * x * (1 + 0.0001 * x) ** (-0.5)
            sigma_z = 0.016 * x * (1 + 0.0003 * x) ** (-1.0)
        else:
            sigma_y = 0.08 * x
            sigma_z = 0.06 * x

        return sigma_y, sigma_z


# ============================
# 3) MÓDULO DE PLUMA
# ============================

class PlumeModule:
    @staticmethod
    def concentracion_gaussiana(Q_gs, H_eff_m, u_ms, x_m, y_m, z_m, sigma_y_m, sigma_z_m):
        x = np.asarray(x_m, dtype=float)
        y = np.asarray(y_m, dtype=float)
        sigma_y = np.asarray(sigma_y_m, dtype=float)
        sigma_z = np.asarray(sigma_z_m, dtype=float)

        C = np.zeros_like(x, dtype=float)
        mask = x > 0.0
        if not np.any(mask):
            return C

        if isinstance(H_eff_m, np.ndarray) and H_eff_m.shape == x.shape:
            H_used = H_eff_m[mask]
        else:
            H_used = float(H_eff_m)

        yv = y[mask]
        syv = sigma_y[mask]
        szv = sigma_z[mask]

        denom = 2.0 * np.pi * float(u_ms) * syv * szv
        denom[denom == 0.0] = 1e-10

        argy = -(yv ** 2) / (2.0 * syv ** 2)
        argz1 = -((float(z_m) - H_used) ** 2) / (2.0 * szv ** 2)
        argz2 = -((float(z_m) + H_used) ** 2) / (2.0 * szv ** 2)

        argy = np.clip(argy, -700.0, 0.0)
        argz1 = np.clip(argz1, -700.0, 0.0)
        argz2 = np.clip(argz2, -700.0, 0.0)

        C[mask] = (float(Q_gs) / denom) * np.exp(argy) * (np.exp(argz1) + np.exp(argz2))
        return C


# ============================
# 3.1) ALTURA EFECTIVA (BRIGGS)
# ============================

def altura_efectiva_briggs_profile(stack_height_m, stack_diameter_m, exit_velocity_ms,
                                   stack_temperature_K, ambient_temperature_K,
                                   wind_speed_ms, x_array_m, clase_estabilidad='D'):
    x = np.asarray(x_array_m, dtype=float)
    g = 9.81

    delta_T = max(float(stack_temperature_K) - float(ambient_temperature_K), 0.0)
    Ts = max(float(stack_temperature_K), 1.0)
    F = g * float(exit_velocity_ms) * (float(stack_diameter_m) ** 2) * delta_T / (4.0 * Ts)

    if (float(stack_diameter_m) <= 0.0 or float(exit_velocity_ms) <= 0.0
            or float(wind_speed_ms) <= 0.0 or F < 1e-3):
        H_field = np.full_like(x, float(stack_height_m), dtype=float)
        return H_field, float(stack_height_m)

    clase = (clase_estabilidad or 'D').upper()
    u = float(wind_speed_ms)
    Hs = float(stack_height_m)
    Ta = max(float(ambient_temperature_K), 1.0)

    if clase in ['A', 'B', 'C', 'D']:
        if F < 55.0:
            x_f = 49.0 * (F ** 0.625)
        else:
            x_f = 119.0 * (F ** 0.4)

        delta_h_max = 1.6 * (F ** (1.0 / 3.0)) * (x_f ** (2.0 / 3.0)) / u
        delta_h_x = 1.6 * (F ** (1.0 / 3.0)) * (np.maximum(x, 0.0) ** (2.0 / 3.0)) / u
        delta_h_x = np.minimum(delta_h_x, delta_h_max)

        H_field = Hs + delta_h_x
        H_final = Hs + delta_h_max
        return H_field, float(H_final)

    if clase == 'E':
        dtheta_dz = 0.020
    else:
        dtheta_dz = 0.035

    s = max((g / Ta) * dtheta_dz, 1e-4)
    delta_h_max = 2.4 * (F / (u * s)) ** (1.0 / 3.0)
    delta_h_tmp = 1.6 * (F ** (1.0 / 3.0)) * (np.maximum(x, 0.0) ** (2.0 / 3.0)) / u
    delta_h_x = np.minimum(delta_h_tmp, delta_h_max)

    H_field = Hs + delta_h_x
    H_final = Hs + delta_h_max
    return H_field, float(H_final)


# ============================
# 4) APLICACIÓN TKINTER (v4.0)
# ============================

class PlumeApp(tk.Tk):
    DEFAULTS = {
        "q": "10.0",
        "h": "50.0",
        "u": "5.0",
        "z_rec": "0.0",
        "max_dist": "5000",
        "trans_width": "1000",
        "d": "2.0",
        "vs": "15.0",
        "Ts": "420.0",
        "Ta": "300.0",
    }

    PG_VALUES = ['Dominante (serie)', 'A', 'B', 'C', 'D', 'E', 'F']

    # Campos numéricos que deben ser > 0 (excepto z_rec que puede ser 0)
    POSITIVE_KEYS = {"q", "h", "u", "max_dist", "trans_width", "d", "vs", "Ts", "Ta"}

    def __init__(self):
        super().__init__()
        self.title("Modelo Gaussiano v4.0 – Briggs, Estabilidades y Corrección de Viento")
        self.geometry("1440x960")
        try:
            self.state("zoomed")
        except Exception:
            pass

        self.use_auto_H = tk.BooleanVar(value=True)
        self.use_wind_correction = tk.BooleanVar(value=True)

        self.freqs_serie = None
        self.clases_serie = None
        self.last_x_axis = None
        self.last_c_axis = None
        self.last_X = None
        self.last_Y = None
        self.last_C = None

        # Lista de widgets Briggs para habilitar/deshabilitar
        self._briggs_widgets = []

        # Definir estilo de validación una sola vez
        try:
            s = ttk.Style()
            s.configure("Error.TEntry", fieldbackground="#FFEBEE")
        except Exception:
            pass

        self._build_ui()
        self._toggle_briggs_fields()
        self._update_all_plots_and_results()

    # ================================================================
    # CONSTRUCCIÓN DE UI
    # ================================================================

    def _build_ui(self):
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        # Marco raíz: columna izquierda (controles) + columna derecha (gráfica)
        root_frame = ttk.Frame(self, padding=8)
        root_frame.grid(row=0, column=0, sticky="nsew")
        root_frame.columnconfigure(1, weight=1)
        root_frame.rowconfigure(0, weight=1)

        self._build_left_panel(root_frame)
        self._build_right_panel(root_frame)

    # ----------------------------------------------------------------
    # PANEL IZQUIERDO
    # ----------------------------------------------------------------

    def _build_left_panel(self, parent):
        """
        Panel izquierdo: controles con scroll + panel de resultados fijo abajo.
        """
        left = ttk.Frame(parent, width=360)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=1)   # scroll ocupa espacio disponible
        left.rowconfigure(1, weight=0)   # separador
        left.rowconfigure(2, weight=0)   # resultados fijos
        left.rowconfigure(3, weight=0)   # exportar

        # ---- Área scrollable de controles ----
        scroll_outer = ttk.Frame(left)
        scroll_outer.grid(row=0, column=0, sticky="nsew")
        scroll_outer.rowconfigure(0, weight=1)
        scroll_outer.columnconfigure(0, weight=1)

        canvas = tk.Canvas(scroll_outer, highlightthickness=0)
        vscroll = ttk.Scrollbar(scroll_outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        vscroll.grid(row=0, column=1, sticky="ns")

        scroll_frame = ttk.Frame(canvas)
        win_id = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-event.delta / 120), "units")

        scroll_frame.bind_all("<MouseWheel>", _on_mousewheel)
        scroll_frame.columnconfigure(0, weight=1)

        self._build_source_section(scroll_frame)
        self._build_briggs_section(scroll_frame)
        self._build_freqs_section(scroll_frame)
        self._build_demo_section(scroll_frame)
        self._build_freq_table_section(scroll_frame)
        self._build_area_section(scroll_frame)

        # ---- Panel de Resultados FIJO (siempre visible) ----
        self._build_results_panel(left)

    def _build_source_section(self, parent):
        """Sección 1: Parámetros de la fuente."""
        ctrl = ttk.LabelFrame(parent, text="Parámetros de la fuente", padding=10)
        ctrl.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        ctrl.columnconfigure(1, weight=1)

        self.entries = {}

        fields = [
            ("q",          "Q – Tasa de emisión (g/s):"),
            ("h",          "Hs – Altura de chimenea (m):"),
            ("u",          "u – Velocidad del viento (m/s):"),
            ("z_rec",      "z receptor (m):"),
            ("max_dist",   "Distancia máxima X (m):"),
            ("trans_width","Ancho transversal total Y (m):"),
        ]

        for i, (key, lbl) in enumerate(fields):
            ttk.Label(ctrl, text=lbl).grid(row=i, column=0, sticky="w", pady=2)
            e = ttk.Entry(ctrl)
            e.insert(0, self.DEFAULTS[key])
            e.grid(row=i, column=1, padx=5, pady=2, sticky="ew")
            self._bind_entry_validation(e, key)
            self.entries[key] = e

        # Clase de estabilidad
        ttk.Label(ctrl, text="Clase de estabilidad:").grid(row=len(fields), column=0, sticky="w")
        self.combo_pg = ttk.Combobox(ctrl, values=self.PG_VALUES, state="readonly")
        self.combo_pg.set("A")
        self.combo_pg.grid(row=len(fields), column=1, padx=5, pady=4, sticky="ew")
        self.combo_pg.bind("<<ComboboxSelected>>", self._on_stability_changed)

        # Advertencia "Dominante sin datos"
        self.lbl_dominante_warn = ttk.Label(
            ctrl, text="⚠ No hay frecuencias cargadas. Se usará clase D.",
            foreground="orange", font=("Helvetica", 8, "italic"), wraplength=220
        )
        # Se muestra u oculta según el estado — por defecto oculta
        self.lbl_dominante_warn.grid(row=len(fields)+1, column=0, columnspan=2, sticky="w", pady=(0, 2))
        self.lbl_dominante_warn.grid_remove()

        row_checks = len(fields) + 2

        # Corrección de viento
        ttk.Checkbutton(
            ctrl,
            text="Corregir u con ley exponencial (u10 → u_eff)",
            variable=self.use_wind_correction,
            command=self._update_all_plots_and_results
        ).grid(row=row_checks, column=0, columnspan=2, sticky="w", pady=(2, 0))

        # ---- Botón principal CALCULAR ----
        btn_frame = ttk.Frame(ctrl)
        btn_frame.grid(row=row_checks+1, column=0, columnspan=2, sticky="ew", pady=(8, 2))
        btn_frame.columnconfigure(0, weight=2)
        btn_frame.columnconfigure(1, weight=1)

        self.btn_calc = ttk.Button(
            btn_frame, text="▶  Calcular", command=self._update_all_plots_and_results
        )
        self.btn_calc.grid(row=0, column=0, sticky="ew", padx=(0, 3))

        ttk.Button(
            btn_frame, text="Cálculo puntual", command=self._calc_point_popup
        ).grid(row=0, column=1, sticky="ew")

        # ---- Botón Ayuda ----
        ttk.Button(
            ctrl, text="ℹ  Información / Ayuda", command=self._show_info_window
        ).grid(row=row_checks+2, column=0, columnspan=2, sticky="ew", pady=(4, 0))

    def _build_briggs_section(self, parent):
        """Sección 2: Elevación de pluma (Briggs) con campos deshabilitables."""
        chim = ttk.LabelFrame(parent, text="Elevación de pluma (Briggs)", padding=10)
        chim.grid(row=1, column=0, sticky="ew", pady=5)
        chim.columnconfigure(1, weight=1)

        # Checkbox primero, con callback que habilita/deshabilita
        cb = ttk.Checkbutton(
            chim,
            text="Calcular altura efectiva H(x) con Briggs",
            variable=self.use_auto_H,
            command=self._on_briggs_toggle
        )
        cb.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

        briggs_fields = [
            ("d",  "d – Diámetro de chimenea (m):"),
            ("vs", "vs – Velocidad de salida (m/s):"),
            ("Ts", "Ts – Temperatura de gases (K):"),
            ("Ta", "Ta – Temperatura ambiente (K):"),
        ]

        for i, (key, lbl) in enumerate(briggs_fields):
            lbl_w = ttk.Label(chim, text=lbl)
            lbl_w.grid(row=i+1, column=0, sticky="w", pady=2)
            e = ttk.Entry(chim)
            e.insert(0, self.DEFAULTS[key])
            e.grid(row=i+1, column=1, padx=5, pady=2, sticky="ew")
            self._bind_entry_validation(e, key)
            self.entries[key] = e
            # Guardar referencias para habilitar/deshabilitar
            self._briggs_widgets.append(lbl_w)
            self._briggs_widgets.append(e)

    def _build_freqs_section(self, parent):
        """Sección 3: Frecuencias manuales."""
        manual = ttk.LabelFrame(parent, text="Frecuencias de estabilidad (manuales)", padding=10)
        manual.grid(row=2, column=0, sticky="ew", pady=5)
        manual.columnconfigure(1, weight=1)
        manual.columnconfigure(3, weight=1)

        ttk.Label(
            manual,
            text="Ingresa valores relativos o porcentajes (se normalizan automáticamente).",
            font=("Helvetica", 8, "italic"), foreground="gray", wraplength=300
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 4))

        self.freq_entries = {}
        for i, c in enumerate("ABC"):
            ttk.Label(manual, text=f"Clase {c}:").grid(row=i+1, column=0, sticky="w")
            e = ttk.Entry(manual, width=7)
            e.insert(0, "0")
            e.grid(row=i+1, column=1, padx=2, pady=2, sticky="ew")
            self.freq_entries[c] = e

        for i, c in enumerate("DEF"):
            ttk.Label(manual, text=f"Clase {c}:").grid(row=i+1, column=2, sticky="w", padx=(12, 0))
            e = ttk.Entry(manual, width=7)
            e.insert(0, "0")
            e.grid(row=i+1, column=3, padx=2, pady=2, sticky="ew")
            self.freq_entries[c] = e

        self.lbl_sum = ttk.Label(manual, text="Suma: 0.00  (se normalizará a 1)", foreground="gray",
                                 font=("Helvetica", 8))
        self.lbl_sum.grid(row=4, column=0, columnspan=4, pady=(4, 2))

        # Actualizar suma en tiempo real
        for e in self.freq_entries.values():
            e.bind("<KeyRelease>", self._update_freq_sum_label)

        ttk.Button(
            manual, text="Aplicar frecuencias manuales", command=self._apply_manual_freqs
        ).grid(row=5, column=0, columnspan=4, sticky="ew", pady=(4, 0))

    def _build_demo_section(self, parent):
        """Sección 4: Generador automático de serie."""
        demo = ttk.LabelFrame(parent, text="Generador automático de serie (24 h)", padding=10)
        demo.grid(row=3, column=0, sticky="ew", pady=5)
        demo.columnconfigure(0, weight=1)
        ttk.Button(
            demo, text="Generar serie demo de 24 h", command=self._gen_demo_series
        ).grid(row=0, column=0, sticky="ew")

    def _build_freq_table_section(self, parent):
        """Sección 5: Tabla de frecuencias A–F."""
        frecs = ttk.LabelFrame(parent, text="Tabla de frecuencias por clase (A–F)", padding=10)
        frecs.grid(row=4, column=0, sticky="ew", pady=5)
        frecs.columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(frecs, columns=("c", "f"), show="headings", height=6)
        self.tree.heading("c", text="Clase")
        self.tree.column("c", width=50, anchor="center")
        self.tree.heading("f", text="Frecuencia")
        self.tree.column("f", width=80, anchor="e")
        self.tree.grid(row=0, column=0, sticky="ew")
        for c in "ABCDEF":
            self.tree.insert("", "end", values=(c, "—"))

    def _build_area_section(self, parent):
        """Sección 6: Análisis de área."""
        iso = ttk.LabelFrame(parent, text="Análisis de área por encima de un límite", padding=10)
        iso.grid(row=5, column=0, sticky="ew", pady=5)
        iso.columnconfigure(1, weight=1)

        ttk.Label(iso, text="Límite de concentración (μg/m³):").grid(row=0, column=0, sticky="w")
        self.ent_iso = ttk.Entry(iso, width=10)
        self.ent_iso.insert(0, "50.0")
        self.ent_iso.grid(row=0, column=1, padx=5, sticky="ew")

        ttk.Button(
            iso, text="Actualizar área", command=self._update_all_plots_and_results
        ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)

        ttk.Label(iso, text="Área afectada (C ≥ límite):").grid(row=2, column=0, sticky="w")
        self.lbl_area = ttk.Label(iso, text="0 m²", font=("Helvetica", 9, "bold"), foreground="blue")
        self.lbl_area.grid(row=2, column=1, sticky="e")

    def _build_results_panel(self, parent):
        """
        Panel de resultados FIJO, siempre visible en la parte inferior izquierda.
        No forma parte del scroll — el usuario lo ve sin importar el desplazamiento.
        """
        # Separador visual (row=1)
        ttk.Separator(parent, orient="horizontal").grid(row=1, column=0, sticky="ew", pady=(4, 2))

        # Panel de resultados (row=2)
        res = ttk.LabelFrame(parent, text="Resultados generales (y = 0, z = z_receptor)", padding=10)
        res.grid(row=2, column=0, sticky="ew", pady=(0, 4))
        res.columnconfigure(1, weight=1)

        rows_res = [
            ("u_eff – Viento efectivo (m/s):",        "lbl_ueff",   "—"),
            ("C_máx – Concentración máx. (μg/m³):",   "lbl_cmax",   "0.00"),
            ("x(C_máx) – Distancia al máximo (m):",   "lbl_xcmax",  "0.00"),
            ("H_final – Altura efectiva (m):",         "lbl_H_eff",  "0.00"),
        ]

        for i, (text, attr, default) in enumerate(rows_res):
            ttk.Label(res, text=text).grid(row=i, column=0, sticky="w", pady=1)
            lbl = ttk.Label(res, text=default, font=("Helvetica", 9, "bold"), foreground="#1565C0")
            lbl.grid(row=i, column=1, sticky="e")
            setattr(self, attr, lbl)

        # ---- Sección de exportación (row=3) ----
        exp = ttk.LabelFrame(parent, text="Exportar resultados", padding=8)
        exp.grid(row=3, column=0, sticky="ew", pady=(0, 6))
        exp.columnconfigure(0, weight=1)
        exp.columnconfigure(1, weight=1)

        ttk.Button(exp, text="💾  Exportar curva (CSV)", command=self._export_csv_data).grid(
            row=0, column=0, sticky="ew", padx=(0, 3), pady=2
        )
        ttk.Button(exp, text="🖼  Guardar gráfica (PNG)", command=self._save_figure).grid(
            row=0, column=1, sticky="ew", pady=2
        )

    # ----------------------------------------------------------------
    # PANEL DERECHO (Gráficas)
    # ----------------------------------------------------------------

    def _build_right_panel(self, parent):
        plotf = ttk.LabelFrame(parent, text="Visualización de resultados", padding=10)
        plotf.grid(row=0, column=1, sticky="nsew")
        plotf.rowconfigure(0, weight=1)
        plotf.columnconfigure(0, weight=1)

        self.fig = Figure(figsize=(10, 8), dpi=100)
        gs = self.fig.add_gridspec(
            2, 2,
            height_ratios=[2.2, 1.0],
            width_ratios=[40.0, 1.0],
            hspace=0.3,
            wspace=0.05
        )
        self.ax_contour = self.fig.add_subplot(gs[0, 0])
        self.ax_cbar = self.fig.add_subplot(gs[0, 1])
        self.ax_line = self.fig.add_subplot(gs[1, 0])
        self.canvas = FigureCanvasTkAgg(self.fig, master=plotf)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

    # ================================================================
    # VALIDACIÓN EN TIEMPO REAL
    # ================================================================

    def _bind_entry_validation(self, entry: ttk.Entry, key: str):
        """Vincula validación visual (borde rojo/verde) y recálculo con Enter."""
        style_ok = "TEntry"

        def validate(_event=None):
            val = entry.get().strip()
            try:
                fval = float(val)
                if key in self.POSITIVE_KEYS and fval <= 0:
                    raise ValueError
                entry.configure(style="TEntry")
            except (ValueError, tk.TclError):
                entry.configure(style="Error.TEntry")

        def on_return(_event=None):
            validate()
            self._update_all_plots_and_results()

        entry.bind("<KeyRelease>", validate)
        entry.bind("<FocusOut>", validate)
        entry.bind("<Return>", on_return)

    # ================================================================
    # CALLBACKS DE CONTROLES
    # ================================================================

    def _on_stability_changed(self, _event=None):
        """Muestra advertencia si se selecciona 'Dominante' sin datos."""
        sel = self.combo_pg.get()
        if sel == "Dominante (serie)" and not self.freqs_serie:
            self.lbl_dominante_warn.grid()
        else:
            self.lbl_dominante_warn.grid_remove()
        self._update_all_plots_and_results()

    def _on_briggs_toggle(self):
        """Habilita o deshabilita los campos de Briggs según el checkbox."""
        self._toggle_briggs_fields()
        self._update_all_plots_and_results()

    def _toggle_briggs_fields(self):
        state = "normal" if self.use_auto_H.get() else "disabled"
        for w in self._briggs_widgets:
            try:
                w.configure(state=state)
            except tk.TclError:
                pass

    def _update_freq_sum_label(self, _event=None):
        """Actualiza etiqueta de suma en tiempo real mientras el usuario escribe."""
        try:
            vals = [float(self.freq_entries[c].get() or 0) for c in "ABCDEF"]
            s = sum(vals)
            color = "green" if s > 0 else "gray"
            self.lbl_sum.configure(
                text=f"Suma: {s:.2f}  (se normalizará a 1)", foreground=color
            )
        except Exception:
            self.lbl_sum.configure(text="Suma: error en valores", foreground="red")

    # ================================================================
    # FRECUENCIAS
    # ================================================================

    def _apply_manual_freqs(self):
        try:
            raw = {c: float(self.freq_entries[c].get()) for c in "ABCDEF"}
            if any(v < 0 for v in raw.values()):
                raise ValueError("Las frecuencias no pueden ser negativas.")
            s = sum(raw.values())
            if s <= 0:
                raise ValueError("La suma de frecuencias debe ser mayor que 0.")
            freqs = {k: v / s for k, v in raw.items()}
            self.freqs_serie = freqs
            self.clases_serie = None
            self._update_freq_table(freqs)
            self.lbl_sum.configure(text=f"Suma: {s:.2f}  → normalizado a 1", foreground="green")

            # Ocultar advertencia si estaba visible
            self.lbl_dominante_warn.grid_remove()

            messagebox.showinfo(
                "Frecuencias aplicadas",
                "Frecuencias manuales aplicadas y normalizadas.\n"
                "La opción 'Dominante (serie)' usará la clase con mayor frecuencia."
            )
        except Exception as e:
            messagebox.showerror("Error en frecuencias", str(e))

    def _update_freq_table(self, freqs: dict):
        for i, c in enumerate("ABCDEF"):
            item = self.tree.get_children()[i]
            self.tree.item(item, values=(c, f"{freqs.get(c, 0.0):.3f}"))

    def _gen_demo_series(self):
        N = 24
        horas = np.arange(N)
        es_dia = np.array([(8 <= h <= 17) for h in horas])
        v = np.linspace(1.5, 6.5, N)

        G = [None] * N
        for i, d in enumerate(es_dia):
            if d and 10 <= horas[i] <= 14:
                G[i] = 800.0
            elif d:
                G[i] = 400.0
            else:
                G[i] = None

        n_ok = [None if d else 2 for d in es_dia]

        self.clases_serie = StabilityModule.series_pg(es_dia, v, G, n_ok)
        self.freqs_serie = StabilityModule.frecuencias(self.clases_serie)
        self._update_freq_table(self.freqs_serie)

        # Ocultar advertencia si estaba visible
        self.lbl_dominante_warn.grid_remove()

        messagebox.showinfo(
            "Serie generada",
            "Serie demo de 24 h generada correctamente.\n"
            "La opción 'Dominante (serie)' usará la clase más frecuente."
        )

    # ================================================================
    # LECTURA Y VALIDACIÓN DE PARÁMETROS
    # ================================================================

    def _read_params(self):
        BRIGGS_KEYS = {"d", "vs", "Ts", "Ta"}
        try:
            vals = {}
            for k, e in self.entries.items():
                # Si Briggs está desactivado, usar los valores por defecto para las claves de Briggs
                # (no se usan en el cálculo, pero evita errores de widget disabled)
                if k in BRIGGS_KEYS and not self.use_auto_H.get():
                    vals[k] = float(self.DEFAULTS[k])
                else:
                    vals[k] = float(e.get())
            if vals["z_rec"] < 0.0:
                raise ValueError("La altura del receptor z debe ser ≥ 0.")
            for k, v in vals.items():
                if k in self.POSITIVE_KEYS and k not in BRIGGS_KEYS and v <= 0.0:
                    raise ValueError(f"El parámetro '{k}' debe ser > 0.")
                if k in BRIGGS_KEYS and self.use_auto_H.get() and v <= 0.0:
                    raise ValueError(f"El parámetro '{k}' debe ser > 0.")
            return vals
        except Exception as e:
            messagebox.showerror("Error en parámetros", str(e))
            return None

    def _selected_class(self):
        sel = self.combo_pg.get()
        if sel == "Dominante (serie)" and self.freqs_serie:
            return max(self.freqs_serie, key=self.freqs_serie.get)
        return sel if sel != "Dominante (serie)" else "D"

    # ================================================================
    # CÁLCULO PRINCIPAL
    # ================================================================

    def _update_all_plots_and_results(self):
        p = self._read_params()
        if p is None:
            return

        # Cursor de espera
        self.config(cursor="watch")
        self.update_idletasks()

        try:
            self._run_calculation(p)
        finally:
            self.config(cursor="")

    def _run_calculation(self, p):
        self.ax_contour.clear()
        self.ax_line.clear()
        self.ax_cbar.clear()

        clase = self._selected_class()

        nx = int(np.clip(p["max_dist"] / 10.0, 150, 400))
        x = np.linspace(0.0, p["max_dist"], nx)
        y = np.linspace(-p["trans_width"] / 2.0, p["trans_width"] / 2.0, nx)
        X, Y = np.meshgrid(x, y)

        u_in = float(p["u"])

        # -------- DOS PASOS PARA u_eff --------
        if self.use_wind_correction.get():
            if self.use_auto_H.get():
                _, H_final_1 = altura_efectiva_briggs_profile(
                    p["h"], p["d"], p["vs"], p["Ts"], p["Ta"], u_in, X, clase
                )
                H_ref = float(H_final_1)
            else:
                H_ref = float(p["h"])
            u_eff = viento_corregido_exponencial(u_in, H_ref, clase)
            u_use = u_eff
        else:
            u_use = u_in

        self.lbl_ueff.config(text=f"{u_use:.2f} m/s")

        # Altura efectiva
        if self.use_auto_H.get():
            H_field, H_final = altura_efectiva_briggs_profile(
                p["h"], p["d"], p["vs"], p["Ts"], p["Ta"], u_use, X, clase
            )
            H_to_use = H_field
            self.lbl_H_eff.config(text=f"{H_final:.1f} m")
        else:
            H_to_use = float(p["h"])
            self.lbl_H_eff.config(text=f"{float(p['h']):.1f} m")

        sigma_y, sigma_z = DispersionModule.sigmas(X, clase)

        Z_g = PlumeModule.concentracion_gaussiana(
            p["q"], H_to_use, u_use, X, Y, p["z_rec"], sigma_y, sigma_z
        )
        Z = Z_g * 1e6

        self.last_X, self.last_Y, self.last_C = X, Y, Z

        # ---- Máximo refinado ----
        finite = np.isfinite(Z)
        max_conc_val = 0.0
        max_conc_x = 0.0

        if np.any(finite):
            idx_flat = np.argmax(Z[finite])
            pos = np.flatnonzero(finite)[idx_flat]
            iy, ix = np.unravel_index(pos, Z.shape)
            approx_x = X[iy, ix]

            search_range = 200.0
            x_min_f = max(1.0, float(approx_x) - search_range)
            x_max_f = min(float(p["max_dist"]), float(approx_x) + search_range)
            x_fine = np.linspace(x_min_f, x_max_f, 1000)
            y_fine = np.zeros_like(x_fine)

            sigma_y_f, sigma_z_f = DispersionModule.sigmas(x_fine, clase)

            if self.use_auto_H.get():
                H_field_f, _ = altura_efectiva_briggs_profile(
                    p["h"], p["d"], p["vs"], p["Ts"], p["Ta"], u_use, x_fine, clase
                )
                H_fine = H_field_f
            else:
                H_fine = float(p["h"])

            C_fine_g = PlumeModule.concentracion_gaussiana(
                p["q"], H_fine, u_use, x_fine, y_fine, p["z_rec"], sigma_y_f, sigma_z_f
            )
            C_fine = C_fine_g * 1e6

            idx_fine = int(np.argmax(C_fine))
            max_conc_val = float(C_fine[idx_fine])
            max_conc_x = float(x_fine[idx_fine])

            self.lbl_cmax.config(text=f"{max_conc_val:.2f} μg/m³")
            self.lbl_xcmax.config(text=f"{max_conc_x:.2f} m")
        else:
            self.lbl_cmax.config(text="0.00")
            self.lbl_xcmax.config(text="0.00")

        # ---- Área por encima del límite ----
        try:
            iso_val = float(self.ent_iso.get())
            if iso_val > 0.0 and np.any(finite) and len(x) > 1 and len(y) > 1:
                dx = x[1] - x[0]
                dy = y[1] - y[0]
                area_m2 = float(np.sum(Z >= iso_val) * dx * dy)
                self.lbl_area.config(text=f"{area_m2:,.0f} m²")
            else:
                self.lbl_area.config(text="0 m²")
        except Exception:
            self.lbl_area.config(text="Error en límite")

        # ---- Mapa de concentración ----
        cont = self.ax_contour.contourf(X, Y, Z, levels=50, cmap="jet", alpha=0.9)
        self.fig.colorbar(cont, cax=self.ax_cbar)

        # Isopleta del límite
        try:
            iso_val = float(self.ent_iso.get())
            if iso_val > 0.0 and iso_val < float(np.nanmax(Z)):
                cs = self.ax_contour.contour(X, Y, Z, levels=[iso_val], colors='magenta', linewidths=2)
                self.ax_contour.clabel(cs, inline=True, fmt=f'{iso_val:.0f}', fontsize=9)
        except Exception:
            pass

        titulo = (
            f"Concentración en el plano (z = {p['z_rec']} m)  |  Clase de estabilidad: {clase}"
        )
        if self.use_wind_correction.get():
            pexp = WIND_EXPONENT_P.get((clase or 'D').upper(), 0.25)
            titulo += f"\np = {pexp:.2f}  |  u_eff = {u_use:.2f} m/s"

        self.ax_contour.set_title(titulo, fontsize=10)
        self.ax_contour.set_xlabel("Distancia longitudinal x (m)")
        self.ax_contour.set_ylabel("Distancia transversal y (m)")
        self.ax_contour.grid(alpha=0.3)

        # ---- Curva y=0 ----
        mid = int(np.argmin(np.abs(y)))
        self.ax_line.plot(x, Z[mid], 'b-', label="C(x, y=0)")
        if max_conc_val > 0.0:
            self.ax_line.plot(max_conc_x, max_conc_val, 'rx', markersize=8, label=f"Máx: {max_conc_val:.2f} μg/m³")
            self.ax_line.legend(fontsize=8)

        self.ax_line.set_xlabel("Distancia x (m)")
        self.ax_line.set_ylabel("Concentración C (μg/m³)")
        self.ax_line.grid(alpha=0.5)
        self.ax_line.set_xlim(0.0, float(p["max_dist"]))

        self.last_x_axis = x
        self.last_c_axis = Z[mid]

        self.canvas.draw_idle()

    # ================================================================
    # CÁLCULO PUNTUAL (POP-UP MEJORADO)
    # ================================================================

    def _calc_point_popup(self):
        w = tk.Toplevel(self)
        w.title("Cálculo puntual de C(x, y, z)")
        w.geometry("420x300")
        w.transient(self)
        w.resizable(False, False)
        w.bind("<Escape>", lambda e: w.destroy())

        frm = ttk.Frame(w, padding=16)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)

        ttk.Label(frm, text="Coordenada x (m):", anchor="w").grid(row=0, column=0, sticky="w", pady=4)
        ex = ttk.Entry(frm)
        ex.grid(row=0, column=1, sticky="ew", padx=8, pady=4)

        ttk.Label(frm, text="Coordenada y (m):", anchor="w").grid(row=1, column=0, sticky="w", pady=4)
        ey = ttk.Entry(frm)
        ey.grid(row=1, column=1, sticky="ew", padx=8, pady=4)
        ttk.Label(frm, text="(vacío = 0)", foreground="gray", font=("Helvetica", 8)).grid(row=1, column=2, padx=4)

        ttk.Label(frm, text="Altura z del receptor (m):", anchor="w").grid(row=2, column=0, sticky="w", pady=4)
        ez = ttk.Entry(frm)
        ez.insert(0, "0.0")
        ez.grid(row=2, column=1, sticky="ew", padx=8, pady=4)

        ttk.Separator(frm, orient="horizontal").grid(row=3, column=0, columnspan=3, sticky="ew", pady=8)

        ttk.Button(frm, text="▶  Calcular", command=lambda: run_calc()).grid(
            row=4, column=0, columnspan=3, sticky="ew", pady=(0, 8)
        )

        # Marco de resultado (con más espacio y fondo destacado)
        res_frame = ttk.LabelFrame(frm, text="Resultado", padding=10)
        res_frame.grid(row=5, column=0, columnspan=3, sticky="ew")
        res_frame.columnconfigure(0, weight=1)

        res_lbl = ttk.Label(
            res_frame, text="—",
            font=("Helvetica", 11, "bold"), foreground="#1565C0",
            wraplength=360, justify="center", anchor="center"
        )
        res_lbl.grid(row=0, column=0, sticky="ew")

        # Enter en cualquier campo también calcula
        for entry in (ex, ey, ez):
            entry.bind("<Return>", lambda e: run_calc())

        def run_calc():
            try:
                x_txt = ex.get().strip()
                if not x_txt:
                    raise ValueError("Debe ingresar la coordenada x.")
                x_in = float(x_txt)

                y_txt = ey.get().strip()
                y_in = 0.0 if not y_txt else float(y_txt)
                z_in = float(ez.get())

                p = self._read_params()
                if not p:
                    return
                clase = self._selected_class()
                u_in = float(p["u"])

                if self.use_wind_correction.get():
                    if self.use_auto_H.get():
                        _, H_final_1 = altura_efectiva_briggs_profile(
                            p["h"], p["d"], p["vs"], p["Ts"], p["Ta"], u_in, np.array([x_in]), clase
                        )
                        H_ref = float(H_final_1)
                    else:
                        H_ref = float(p["h"])
                    u_use = viento_corregido_exponencial(u_in, H_ref, clase)
                else:
                    u_use = u_in

                if self.use_auto_H.get():
                    H_field_pt, _ = altura_efectiva_briggs_profile(
                        p["h"], p["d"], p["vs"], p["Ts"], p["Ta"], u_use, np.array([x_in]), clase
                    )
                    H_pt = float(H_field_pt[0])
                else:
                    H_pt = float(p["h"])

                sigma_y_pt, sigma_z_pt = DispersionModule.sigmas(np.array([x_in]), clase)
                C_pt_g = PlumeModule.concentracion_gaussiana(
                    p["q"], H_pt, u_use,
                    np.array([x_in]), np.array([y_in]), z_in,
                    sigma_y_pt, sigma_z_pt
                )
                C_pt_ug = float(C_pt_g[0] * 1e6)
                res_lbl.config(
                    text=f"C = {C_pt_ug:.4f} μg/m³\n"
                         f"u_eff = {u_use:.3f} m/s  |  H_eff = {H_pt:.2f} m",
                    foreground="#1565C0"
                )
            except ValueError as e:
                res_lbl.config(text=f"⚠ {e}", foreground="red")
            except Exception:
                res_lbl.config(text="⚠ Error: revise los datos de entrada.", foreground="red")

    # ================================================================
    # EXPORTAR Y GUARDAR
    # ================================================================

    def _export_csv_data(self):
        if self.last_x_axis is None or self.last_c_axis is None:
            messagebox.showwarning("Sin datos", "Primero ejecute el modelo para generar la curva.")
            return

        fpath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("Todos los archivos", "*.*")]
        )
        if not fpath:
            return

        try:
            with open(fpath, 'w', newline='', encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile, delimiter=';')
                writer.writerow(["Distancia_x_m", "Concentracion_y0_ugm3"])
                for x_val, c_val in zip(self.last_x_axis, self.last_c_axis):
                    writer.writerow([f"{x_val:.2f}", f"{c_val:.6f}"])
            messagebox.showinfo("Exportado", "Curva exportada correctamente.")
        except Exception as e:
            messagebox.showerror("Error al exportar", str(e))

    def _save_figure(self):
        fpath = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("Todos los archivos", "*.*")]
        )
        if not fpath:
            return

        try:
            self.fig.savefig(fpath, dpi=300)
            messagebox.showinfo("Guardado", "Gráfica guardada en alta resolución (300 dpi).")
        except Exception as e:
            messagebox.showerror("Error al guardar", str(e))

    # ================================================================
    # VENTANA DE INFORMACIÓN / AYUDA
    # ================================================================

    def _show_info_window(self):
        win = tk.Toplevel(self)
        win.title("Información técnica – Modelo de pluma gaussiana")
        win.geometry("960x720")
        win.transient(self)
        win.bind("<Escape>", lambda e: win.destroy())

        # Barra superior con botón Cerrar visible
        top_bar = ttk.Frame(win, padding=(10, 6, 10, 0))
        top_bar.pack(fill="x")
        ttk.Label(top_bar, text="Información técnica del modelo", font=("Helvetica", 11, "bold")).pack(side="left")
        ttk.Button(top_bar, text="✕  Cerrar", command=win.destroy).pack(side="right")

        ttk.Separator(win, orient="horizontal").pack(fill="x", pady=(6, 0))

        # Contenedor con scroll
        container = ttk.Frame(win, padding=10)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, highlightthickness=0)
        vscroll = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        vscroll.grid(row=0, column=1, sticky="ns")
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        content = ttk.Frame(canvas)
        win_id = canvas.create_window((0, 0), window=content, anchor="nw")

        content.bind("<Configure>", lambda _: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))

        font_body = ("Helvetica", 10)
        font_mono = ("Courier New", 10)

        # Bloque 1: Introducción
        head = ttk.LabelFrame(content, text="Modelo de pluma gaussiana – Descripción general", padding=10)
        head.pack(fill="x", pady=(0, 8))
        ttk.Label(head, text=(
            "Esta herramienta implementa el modelo de pluma gaussiana para una fuente puntual elevada, "
            "incorporando dispersión atmosférica por clase de estabilidad Pasquill-Gifford (A–F) y, "
            "opcionalmente, elevación de pluma según Briggs y corrección vertical de la velocidad del "
            "viento por ley exponencial."
        ), wraplength=880, justify="left", font=font_body).pack(anchor="w")

        # Bloque 2: Ecuación
        eq = ttk.LabelFrame(content, text="Ecuación de concentración (estado estacionario, reflexión en el suelo)", padding=10)
        eq.pack(fill="x", pady=8)
        ttk.Label(eq, font=font_mono, wraplength=880, justify="left", text=(
            "C(x,y,z) = Q / (2π·u·σy·σz)\n"
            "         · exp(−y²/(2σy²))\n"
            "         · [ exp(−(z−H)²/(2σz²)) + exp(−(z+H)²/(2σz²)) ]"
        )).pack(anchor="w")

        # Bloque 3: Variables
        varf = ttk.LabelFrame(content, text="Definición de variables", padding=10)
        varf.pack(fill="x", pady=8)
        ttk.Label(varf, font=font_body, justify="left", text=(
            "Q   : tasa de emisión (g/s)\n"
            "u   : velocidad del viento efectiva (m/s)\n"
            "σy  : coeficiente de dispersión transversal (m)\n"
            "σz  : coeficiente de dispersión vertical (m)\n"
            "H   : altura efectiva de la fuente (m)\n"
            "x, y: coordenadas longitudinal y transversal (m)\n"
            "z   : altura del receptor (m)"
        )).pack(anchor="w")

        # Bloque 4: Estabilidad
        stab = ttk.LabelFrame(content, text="Clases de estabilidad atmosférica (Pasquill–Gifford)", padding=10)
        stab.pack(fill="x", pady=8)
        ttk.Label(stab, wraplength=880, justify="left", font=font_body, text=(
            "La estabilidad se define entre A (muy inestable) y F (muy estable). Esta condición controla "
            "la intensidad de la turbulencia atmosférica y determina la magnitud de σy(x) y σz(x). "
            "Se puede seleccionar una clase fija (A–F) o usar 'Dominante (serie)' a partir de "
            "frecuencias cargadas manualmente o generadas con la serie demo de 24 h."
        )).pack(anchor="w")

        # Bloque 5: Briggs
        brig = ttk.LabelFrame(content, text="Altura efectiva – Elevación de pluma (Briggs)", padding=10)
        brig.pack(fill="x", pady=8)
        ttk.Label(brig, wraplength=880, justify="left", font=font_body, text=(
            "Cuando la elevación de pluma está habilitada se adopta:\n\n"
            "  H(x) = Hs + Δh(x)\n\n"
            "donde Hs es la altura geométrica de la chimenea y Δh(x) corresponde al ascenso "
            "por flotabilidad. El término Δh(x) depende del flujo de flotabilidad F y varía "
            "según el régimen de estabilidad:\n"
            "  · A–D (inestable / neutral): mayor mezcla y ascenso relativo.\n"
            "  · E–F (estable): la estratificación limita el ascenso y reduce la altura efectiva."
        )).pack(anchor="w")

        # Bloque 6: Corrección viento
        wind = ttk.LabelFrame(content, text="Corrección de velocidad del viento (ley exponencial)", padding=10)
        wind.pack(fill="x", pady=8)
        ttk.Label(wind, wraplength=880, justify="left", font=font_body, text=(
            "La velocidad de entrada se interpreta como u₁₀ (medida a 10 m). "
            "Si la corrección está habilitada, se ajusta a una altura representativa mediante:\n\n"
            "  u(z) = u₁₀ · (z/10)^p\n\n"
            "El exponente p se asigna según la clase de estabilidad:\n"
            "  A: 0.15 · B: 0.15 · C: 0.20 · D: 0.25 · E: 0.40 · F: 0.60\n\n"
            "La velocidad representativa usada en los cálculos es:\n"
            "  u_eff = u₁₀ · (H_ref/10)^p\n"
            "donde H_ref se toma como H_final cuando Briggs está activo, o como Hs en caso contrario."
        )).pack(anchor="w")

        # Bloque 7: Procedimiento
        proc = ttk.LabelFrame(content, text="Procedimiento de cálculo (esquema de dos etapas)", padding=10)
        proc.pack(fill="x", pady=8)
        ttk.Label(proc, wraplength=880, justify="left", font=font_body, text=(
            "1) Estimar H_ref usando inicialmente u = u₁₀.\n"
            "2) Calcular u_eff con H_ref y recalcular H(x) y C(x,y,z) usando u_eff.\n\n"
            "Este esquema mejora la coherencia física al considerar el incremento de velocidad "
            "con la altura, manteniendo una formulación operativa adecuada para análisis y enseñanza."
        )).pack(anchor="w")

        # Bloque 8: Limitaciones
        lim = ttk.LabelFrame(content, text="Limitaciones del modelo", padding=10)
        lim.pack(fill="x", pady=(8, 12))
        ttk.Label(lim, font=font_body, justify="left", text=(
            "· Emisión continua y condiciones estacionarias.\n"
            "· Viento horizontal uniforme (sin cambio de dirección).\n"
            "· Terreno plano; no incluye edificios ni efectos topográficos.\n"
            "· No incluye deposición, química atmosférica ni lavado por lluvia.\n"
            "· No es representativo muy cerca de la fuente (zona de chorro)."
        )).pack(anchor="w")

        # Botón cerrar al final del contenido
        ttk.Button(content, text="✕  Cerrar", command=win.destroy).pack(pady=(0, 10))


if __name__ == "__main__":
    app = PlumeApp()
    app.mainloop()