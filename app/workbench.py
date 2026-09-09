# -*- coding: utf-8 -*-
"""Main "Banco de trabajo" view (mockup 1a): a workflow stage rail, a
paged parameter column, and a results column with a spec-tile header,
the concentration map and the centerline profile.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from . import plot_style
from .model import format_area
from .theme import COLORS
from .widgets import (
    BlueprintFrame, ClassSegmented, ErrorBanner, RampLegend, Section, SpecTile,
    StabilityBadge, ValidatedField, VerticalStepRail,
)

STEPS = [
    ("fuente", "Fuente"),
    ("meteo", "Meteorología"),
    ("dominio", "Dominio y receptor"),
    ("analisis", "Análisis"),
]


class WorkbenchView:
    def __init__(self, parent: tk.Widget, app):
        self.app = app
        self.fonts = app.fonts
        self.fields: dict[str, ValidatedField] = {}
        self.freq_fields: dict[str, tk.StringVar] = {}

        self.root = ttk.Frame(parent)
        self.root.pack(fill="both", expand=True)
        self.root.columnconfigure(2, weight=1)
        self.root.rowconfigure(0, weight=1)

        self._build_rail()
        self._build_param_column()
        self._build_results_column()

        self.show_step("fuente")
        self._sync_briggs_enabled()
        self.refresh()

    # ------------------------------------------------------------------
    # Column 1: workflow rail
    # ------------------------------------------------------------------

    def _build_rail(self) -> None:
        rail = ttk.Frame(self.root, width=210)
        rail.grid(row=0, column=0, sticky="ns")
        rail.grid_propagate(False)
        rail.rowconfigure(2, weight=1)

        wrap = ttk.Frame(rail, padding=(0, 16, 0, 0))
        wrap.grid(row=0, column=0, sticky="new")
        sec = Section(wrap, "Flujo de trabajo", self.fonts)
        sec.pack(fill="x", padx=14)
        self.rail = VerticalStepRail(sec.body, STEPS, self.fonts, on_select=self.show_step)
        self.rail.pack(fill="x")

        stab_wrap = ttk.Frame(rail, padding=(14, 16, 14, 0))
        stab_wrap.grid(row=1, column=0, sticky="new")
        sep = tk.Frame(stab_wrap, height=1, bg=COLORS["divider"])
        sep.pack(fill="x", pady=(0, 14))
        stab_sec = Section(stab_wrap, "Estabilidad activa", self.fonts)
        stab_sec.pack(fill="x")
        self.badge = StabilityBadge(stab_sec.body, self.fonts)
        self.badge.pack(fill="x")

        exp_wrap = ttk.Frame(rail, padding=(14, 10, 14, 12))
        exp_wrap.grid(row=3, column=0, sticky="sew")
        exp_sec = Section(exp_wrap, "Exportar", self.fonts)
        exp_sec.pack(fill="x")
        ttk.Button(exp_sec.body, text="Curva (CSV)", style="Secondary.TButton",
                   command=self.app.export_csv).pack(fill="x", pady=(0, 5))
        ttk.Button(exp_sec.body, text="Gráfica (PNG 300 dpi)", style="Secondary.TButton",
                   command=self.app.save_png).pack(fill="x", pady=(0, 5))
        ttk.Button(exp_sec.body, text="Informe del caso", style="Secondary.TButton",
                   command=self.app.export_report).pack(fill="x")

    # ------------------------------------------------------------------
    # Column 2: paged parameter column
    # ------------------------------------------------------------------

    def _build_param_column(self) -> None:
        col = ttk.Frame(self.root, width=352)
        col.grid(row=0, column=1, sticky="ns")
        col.grid_propagate(False)
        col.rowconfigure(1, weight=1)

        header = ttk.Frame(col, padding=(16, 16, 16, 6))
        header.grid(row=0, column=0, sticky="ew")
        self.step_title_var = tk.StringVar()
        ttk.Label(header, textvariable=self.step_title_var, style="Heading.TLabel").pack(side="left")
        self.step_count_var = tk.StringVar()
        ttk.Label(header, textvariable=self.step_count_var, style="Faint.TLabel").pack(side="right")

        body = ttk.Frame(col)
        body.grid(row=1, column=0, sticky="nsew", padx=16)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        self.panels: dict[str, ttk.Frame] = {}
        for step_id, _ in STEPS:
            panel = ttk.Frame(body)
            panel.grid(row=0, column=0, sticky="new")
            panel.grid_remove()
            self.panels[step_id] = panel

        self._build_step_fuente(self.panels["fuente"])
        self._build_step_meteo(self.panels["meteo"])
        self._build_step_dominio(self.panels["dominio"])
        self._build_step_analisis(self.panels["analisis"])

        footer = ttk.Frame(col, padding=16)
        footer.grid(row=2, column=0, sticky="sew")
        btn_row = ttk.Frame(footer)
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="▶  Calcular", style="Primary.TButton",
                   command=self.app.recompute).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(btn_row, text="Punto", style="Secondary.TButton",
                   command=self.app.open_point_dialog).pack(side="left")
        ttk.Label(footer, text="Enter en cualquier campo recalcula", style="Faint.TLabel").pack(anchor="w", pady=(7, 0))

    def show_step(self, step_id: str) -> None:
        for sid, panel in self.panels.items():
            panel.grid() if sid == step_id else panel.grid_remove()
        self.rail.set_active(step_id)
        idx = [s for s, _ in STEPS].index(step_id) + 1
        label = dict(STEPS)[step_id]
        self.step_title_var.set(label if step_id != "fuente" else "Parámetros de la fuente")
        self.step_count_var.set(f"{idx} / {len(STEPS)}")

    def _field(self, parent, key, label, unit, rule=None, hint=None, width=None,
               wrap=240, error_host=None):
        default = getattr(self.app.p, key)
        f = ValidatedField(parent, label, unit, default, self.fonts, rule=rule,
                            on_commit=lambda k=key: self._commit_field(k), hint=hint, width=width,
                            wrap=wrap, error_host=error_host)
        self.fields[key] = f
        return f

    def _commit_field(self, key: str) -> None:
        setattr(self.app.p, key, self.fields[key].value)
        self.app.recompute()

    def _build_step_fuente(self, parent: ttk.Frame) -> None:
        grid = ttk.Frame(parent)
        grid.pack(fill="x")
        grid.columnconfigure((0, 1), weight=1)
        self.ta_banner = ErrorBanner(parent, "Ta", self.fonts, wrap=250)

        specs = [
            ("q", "Q — Emisión", "g/s", True),
            ("h", "Hs — Chimenea", "m", True),
            ("d", "d — Diámetro", "m", True),
            ("vs", "vs — Salida", "m/s", True),
            ("Ts", "Ts — Gases", "K", True),
            ("Ta", "Ta — Ambiente", "K", None),
        ]
        pos_rule = lambda v: (v > 0, "Debe ser mayor que 0.")
        for i, (key, label, unit, positive) in enumerate(specs):
            r, c = divmod(i, 2)
            if key == "Ta":
                def ta_rule(v, self=self):
                    if not self.app.p.use_auto_H:
                        return True, ""
                    ts = self.fields["Ts"].value
                    if v >= ts:
                        return False, (f"Ta debe ser menor que Ts ({ts:g} K) para que exista flotabilidad; "
                                       "con Ts ≤ Ta la pluma no asciende y H = Hs.")
                    return True, ""
                f = self._field(grid, key, label, unit, rule=ta_rule, width=9,
                                 error_host=self.ta_banner)
            else:
                hint = "Típico de chimenea industrial: 5 – 25 m/s" if key == "vs" else None
                f = self._field(grid, key, label, unit, rule=pos_rule if positive else None,
                                 hint=hint, width=9, wrap=145)
            f.grid(row=r, column=c, sticky="ew", padx=(0 if c == 0 else 12, 0), pady=(0, 11))
        self.ta_banner.pack(fill="x", pady=(0, 4))

        assume = Section(parent, "Supuestos activos", self.fonts, divider_above=True)
        assume.pack(fill="x", pady=(18, 0))
        cb1 = ttk.Checkbutton(assume.body, text="Elevación de pluma con Briggs — H(x) = Hs + Δh(x)",
                              variable=self.app.use_auto_H_var, command=self._on_briggs_toggle)
        cb1.pack(anchor="w", pady=(0, 8))
        cb2 = ttk.Checkbutton(assume.body, text="Corregir viento con ley exponencial — u(z) = u₁₀·(z/10)^p",
                              variable=self.app.use_wind_var, command=self.app.recompute)
        cb2.pack(anchor="w")

        chain = Section(parent, "Cadena de cálculo", self.fonts, divider_above=True)
        chain.pack(fill="x", pady=(18, 0))
        self.chain_vars = {k: tk.StringVar(value="—") for k in ("F", "dh", "ueff")}
        for label, key, unit in [("F flotabilidad", "F", "m⁴/s³"), ("Δh máx", "dh", "m"), ("u₁₀ → u_eff", "ueff", "")]:
            row = ttk.Frame(chain.body)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=label, style="Mono.TLabel").pack(side="left")
            ttk.Label(row, textvariable=self.chain_vars[key], style="Accent.TLabel").pack(side="right")

    def _sync_briggs_enabled(self) -> None:
        enabled = self.app.use_auto_H_var.get()
        for key in ("d", "vs", "Ts", "Ta"):
            self.fields[key].set_enabled(enabled)

    def _on_briggs_toggle(self) -> None:
        self._sync_briggs_enabled()
        self.app.recompute()

    def _build_step_meteo(self, parent: ttk.Frame) -> None:
        f = self._field(parent, "u", "u₁₀ — Viento", "m/s", rule=lambda v: (v > 0, "Debe ser mayor que 0."))
        f.pack(fill="x", pady=(0, 14))

        sec = Section(parent, "Clase de estabilidad", self.fonts)
        sec.pack(fill="x")
        self.class_var = tk.StringVar(value=self.app.p.clase)
        ClassSegmented(sec.body, self.class_var, command=self._on_class_pick).pack(fill="x")

        self.use_dominant_var = tk.BooleanVar(value=self.app.dominant_enabled)
        ttk.Checkbutton(sec.body, text="Usar clase dominante de la serie (24 h)",
                        variable=self.use_dominant_var, command=self._on_dominant_toggle
                        ).pack(anchor="w", pady=(10, 0))

        self.warn_var = tk.StringVar(value="⚠ No hay frecuencias cargadas. Se usará clase D.")
        self.warn_lbl = ttk.Label(sec.body, textvariable=self.warn_var, style="WarnBanner.TLabel",
                                   wraplength=280, justify="left", padding=8)

        freqs_sec = Section(parent, "Frecuencias manuales (A–F)", self.fonts, divider_above=True)
        freqs_sec.pack(fill="x", pady=(18, 0))
        ttk.Label(freqs_sec.body, text="Valores relativos o porcentajes; se normalizan al aplicar.",
                  style="Faint.TLabel", wraplength=280, justify="left").pack(anchor="w", pady=(0, 8))
        fgrid = ttk.Frame(freqs_sec.body)
        fgrid.pack(fill="x")
        for i, c in enumerate("ABCDEF"):
            r, col = divmod(i, 2)
            cell = ttk.Frame(fgrid)
            cell.grid(row=r, column=col, sticky="ew", padx=(0 if col == 0 else 10, 0), pady=3)
            fgrid.columnconfigure(col, weight=1)
            ttk.Label(cell, text=f"Clase {c}", style="Soft.TLabel", width=8).pack(side="left")
            var = tk.StringVar(value="0")
            ttk.Entry(cell, textvariable=var, width=6).pack(side="left", padx=(6, 0))
            self.freq_fields[c] = var
        self.freq_sum_var = tk.StringVar(value="Suma: 0.00 (se normalizará a 1)")
        ttk.Label(freqs_sec.body, textvariable=self.freq_sum_var, style="Faint.TLabel").pack(anchor="w", pady=(8, 6))
        ttk.Button(freqs_sec.body, text="Aplicar frecuencias manuales", style="Secondary.TButton",
                   command=self.app.apply_manual_freqs).pack(fill="x")
        ttk.Button(freqs_sec.body, text="Generar serie demo de 24 h", style="Secondary.TButton",
                   command=self.app.generate_demo_series).pack(fill="x", pady=(8, 0))

        table_sec = Section(parent, "Tabla de frecuencias", self.fonts, divider_above=True)
        table_sec.pack(fill="x", pady=(18, 0))
        self.freq_table = ttk.Treeview(table_sec.body, columns=("c", "f"), show="headings", height=6)
        self.freq_table.heading("c", text="Clase")
        self.freq_table.column("c", width=60, anchor="center")
        self.freq_table.heading("f", text="Frecuencia")
        self.freq_table.column("f", width=90, anchor="e")
        self.freq_table.pack(fill="x")
        for c in "ABCDEF":
            self.freq_table.insert("", "end", iid=c, values=(c, "—"))

    def _on_class_pick(self) -> None:
        self.use_dominant_var.set(False)
        self.app.dominant_enabled = False
        self.app.p.clase = self.class_var.get()
        self.app.recompute()

    def _on_dominant_toggle(self) -> None:
        self.app.dominant_enabled = self.use_dominant_var.get()
        self.app.recompute()

    def _build_step_dominio(self, parent: ttk.Frame) -> None:
        pos_rule = lambda v: (v > 0, "Debe ser mayor que 0.")
        f1 = self._field(parent, "max_dist", "X máx — Distancia longitudinal", "m", rule=pos_rule)
        f1.pack(fill="x", pady=(0, 14))
        f2 = self._field(parent, "trans_width", "Ancho Y — Extensión transversal", "m", rule=pos_rule)
        f2.pack(fill="x", pady=(0, 14))
        f3 = self._field(parent, "z_rec", "z receptor — Altura de muestreo", "m",
                          rule=lambda v: (v >= 0, "Debe ser ≥ 0."))
        f3.pack(fill="x")
        ttk.Label(parent, text="Malla 400 × 400 · reflexión en el suelo · emisión continua, terreno plano.",
                  style="Faint.TLabel", wraplength=280, justify="left").pack(anchor="w", pady=(18, 0))

    def _build_step_analisis(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Cálculo puntual", style="Heading.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Label(parent, text="Concentración en un punto (x, y, z) específico del dominio.",
                  style="Soft.TLabel", wraplength=280, justify="left").pack(anchor="w", pady=(0, 12))

        grid = ttk.Frame(parent)
        grid.pack(fill="x")
        grid.columnconfigure((0, 1, 2), weight=1)
        self.pt_x = tk.StringVar(value="2400")
        self.pt_y = tk.StringVar(value="0")
        self.pt_z = tk.StringVar(value="1.5")
        for i, (label, var) in enumerate([("x (m)", self.pt_x), ("y (m)", self.pt_y), ("z (m)", self.pt_z)]):
            cell = ttk.Frame(grid)
            cell.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 8, 0))
            ttk.Label(cell, text=label, style="Soft.TLabel").pack(anchor="w")
            ttk.Entry(cell, textvariable=var, width=6).pack(fill="x", pady=(4, 0))

        ttk.Button(parent, text="▶  Calcular en este punto", style="Primary.TButton",
                   command=self._calc_point_inline).pack(fill="x", pady=(12, 0))

        result = BlueprintFrame(parent)
        result.pack(fill="x", pady=(14, 0))
        inner = ttk.Frame(result, padding=14)
        inner.pack(fill="x")
        ttk.Label(inner, text="RESULTADO", style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        row = ttk.Frame(inner)
        row.pack(anchor="w", fill="x")
        self.pt_result_var = tk.StringVar(value="—")
        tk.Label(row, textvariable=self.pt_result_var, font=self.fonts.spec_n,
                 bg=COLORS["bg"], fg=COLORS["accent_900"]).pack(side="left")
        ttk.Label(row, text=" μg/m³", style="Faint.TLabel").pack(side="left", anchor="s", pady=(0, 4))
        self.pt_detail_var = tk.StringVar(value="")
        ttk.Label(inner, textvariable=self.pt_detail_var, style="Mono.TLabel", wraplength=260,
                  justify="left").pack(anchor="w", pady=(8, 0))

    def _calc_point_inline(self) -> None:
        try:
            x, y, z = float(self.pt_x.get()), float(self.pt_y.get()), float(self.pt_z.get())
        except ValueError:
            self.pt_result_var.set("⚠")
            self.pt_detail_var.set("Revisa los valores de x, y, z.")
            return
        self.app.calc_point(x, y, z)

    def show_point_result(self, x, y, z, r: dict) -> None:
        self.pt_result_var.set(f"{r['c']:.2f}")
        self.pt_detail_var.set(f"u_eff {r['u_eff']:.2f} m/s · H_eff {r['h']:.1f} m\n"
                                f"σy {r['sigma_y']:.0f} m · σz {r['sigma_z']:.0f} m")

    # ------------------------------------------------------------------
    # Column 3: results + plots
    # ------------------------------------------------------------------

    def _build_results_column(self) -> None:
        col = ttk.Frame(self.root, padding=(18, 16, 18, 18))
        col.grid(row=0, column=2, sticky="nsew")
        col.rowconfigure(2, weight=1)  # the plot row absorbs resizing
        col.columnconfigure(0, weight=1)

        tiles = ttk.Frame(col)
        tiles.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        for i in range(4):
            tiles.columnconfigure(i, weight=1)
        self.tile_cmax = self._tile_in(tiles, 0, "C MÁX", "μg/m³")
        self.tile_xmax = self._tile_in(tiles, 1, "X EN C MÁX", "m")
        self.tile_h = self._tile_in(tiles, 2, "H EFECTIVA", "m")
        self.tile_u = self._tile_in(tiles, 3, "U EFECTIVO", "m/s")

        head = ttk.Frame(col)
        head.grid(row=1, column=0, sticky="ew")
        self.map_title_var = tk.StringVar()
        ttk.Label(head, textvariable=self.map_title_var, style="Heading.TLabel").pack(side="left")
        self.map_meta_var = tk.StringVar()
        ttk.Label(head, textvariable=self.map_meta_var, style="Faint.TLabel").pack(side="left", padx=(10, 0))

        plot_row = ttk.Frame(col)
        plot_row.grid(row=2, column=0, sticky="nsew", pady=(9, 18))
        plot_row.columnconfigure(0, weight=1)
        plot_row.rowconfigure(0, weight=1)

        canvas_frame = BlueprintFrame(plot_row, width=600, height=320)
        canvas_frame.grid(row=0, column=0, sticky="nsew")
        # The Tk canvas re-requests its rendered size on every resize; stop
        # that request from propagating or the window can never shrink.
        canvas_frame.pack_propagate(False)
        self.fig = plot_style.new_figure(figsize=(9, 5.4))
        gs = self.fig.add_gridspec(2, 1, height_ratios=[2.2, 1.0], hspace=0.42,
                                   left=0.07, right=0.98, top=0.985, bottom=0.10)
        self.ax_contour = self.fig.add_subplot(gs[0])
        self.ax_line = self.fig.add_subplot(gs[1])
        self.canvas = FigureCanvasTkAgg(self.fig, master=canvas_frame)
        self.canvas.get_tk_widget().configure(bg=COLORS["bg"], highlightthickness=0)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=1, pady=1)

        legend_col = ttk.Frame(plot_row, width=54)
        legend_col.grid(row=0, column=1, sticky="ns", padx=(10, 0))
        self.legend_top_var = tk.StringVar(value="0")
        ttk.Label(legend_col, textvariable=self.legend_top_var, style="Faint.TLabel").pack(anchor="w")
        RampLegend(legend_col, width=18, height=230).pack(pady=4)
        ttk.Label(legend_col, text="0", style="Faint.TLabel").pack(anchor="w")

        footer = ttk.Frame(col)
        footer.grid(row=3, column=0, sticky="sew")
        footer.columnconfigure(2, weight=1)
        self.iso_field = ValidatedField(footer, "Límite de concentración", "μg/m³", self.app.iso_val, self.fonts,
                                         rule=lambda v: (v > 0, "Debe ser mayor que 0."),
                                         on_commit=self._commit_iso, width=14)
        self.iso_field.grid(row=0, column=0, sticky="w")

        area_wrap = ttk.Frame(footer, padding=(24, 0, 0, 0))
        area_wrap.grid(row=0, column=1, sticky="w")
        self.tile_area = SpecTile(area_wrap, "ÁREA CON C ≥ LÍMITE", "m²", self.fonts)
        self.tile_area.pack()

        ttk.Label(footer, text="Malla 400 × 400 · reflexión en el suelo\nemisión continua, terreno plano",
                  style="Faint.TLabel", justify="right").grid(row=0, column=2, sticky="e")

    def _tile_in(self, parent, col, caption, unit):
        wrap = BlueprintFrame(parent, corners=False)
        wrap.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 1, 0))
        tile = SpecTile(wrap, caption, unit, self.fonts)
        tile.pack(fill="both")
        return tile

    def _commit_iso(self) -> None:
        self.app.iso_val = self.iso_field.value
        self.app.recompute()

    # ------------------------------------------------------------------
    # Refresh from a computed Result
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        r = self.app.result
        if r is None:
            return
        self.tile_cmax.set(f"{r.cmax:.1f}")
        self.tile_xmax.set(f"{r.xmax:.0f}")
        self.tile_h.set(f"{r.H_final:.1f}")
        self.tile_u.set(f"{r.u_eff:.2f}")
        self.tile_area.set(format_area(r.area_m2))

        self.badge.set_class(self.app.p.clase, r.p)
        self.map_title_var.set(f"Concentración en el plano z = {self.app.p.z_rec:g} m")
        self.map_meta_var.set(f"dominio {self.app.p.max_dist:g} × {self.app.p.trans_width:g} m · "
                               f"clase {self.app.p.clase} · isopleta {self.app.iso_val:g} μg/m³")
        self.legend_top_var.set(f"{r.cmax:.0f}")

        self.chain_vars["F"].set(f"{r.F:.1f}")
        self.chain_vars["dh"].set(f"{max(r.H_final - self.app.p.h, 0):.1f}")
        self.chain_vars["ueff"].set(f"{self.app.p.u:.1f} → {r.u_eff:.2f} m/s")

        point = None
        if self.app.last_point is not None:
            point = (self.app.last_point["x"], self.app.last_point["y"])
        plot_style.draw_contour(self.ax_contour, r, point=point)
        plot_style.draw_line(self.ax_line, r)
        self.canvas.draw_idle()

        show_warn = self.app.dominant_enabled and not self.app.freqs_serie
        if show_warn and not self.warn_lbl.winfo_ismapped():
            self.warn_lbl.pack(anchor="w", pady=(10, 0), fill="x")
        elif not show_warn and self.warn_lbl.winfo_ismapped():
            self.warn_lbl.pack_forget()

        if self.app.freqs_serie:
            for c in "ABCDEF":
                self.freq_table.item(c, values=(c, f"{self.app.freqs_serie.get(c, 0.0):.3f}"))
