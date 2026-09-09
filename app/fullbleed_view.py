# -*- coding: utf-8 -*-
""""Mapa a sangre" alternate layout (mockup 1b): a compact parameter
ribbon on top, the concentration map filling the window with floating
result/point-inspector cards, and a profile + frequency strip below.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from . import plot_style
from .theme import COLORS
from .widgets import BlueprintFrame, ClassSegmented, Section, ValidatedField


class FullBleedView:
    def __init__(self, parent: tk.Widget, app):
        self.app = app
        self.fonts = app.fonts
        self.fields: dict[str, ValidatedField] = {}

        self.root = ttk.Frame(parent)
        self.root.pack(fill="both", expand=True)
        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)

        self._build_ribbon()
        self._build_map_area()
        self._build_bottom_strip()
        self._sync_briggs_enabled()
        self.refresh()

    # ------------------------------------------------------------------
    def _field(self, parent, key, label, unit=None, rule=None):
        default = getattr(self.app.p, key)
        f = ValidatedField(parent, label, unit or "", default, self.fonts, rule=rule,
                            on_commit=lambda k=key: self._commit(k), width=8)
        self.fields[key] = f
        return f

    def _commit(self, key: str) -> None:
        setattr(self.app.p, key, self.fields[key].value)
        self.app.recompute()

    def _build_ribbon(self) -> None:
        ribbon = ttk.Frame(self.root)
        ribbon.grid(row=0, column=0, sticky="ew")
        for i in range(4):
            ribbon.columnconfigure(i, weight=1)
        pos = lambda v: (v > 0, "Debe ser mayor que 0.")

        c0 = ttk.Frame(ribbon, padding=12)
        c0.grid(row=0, column=0, sticky="nsew")
        s0 = Section(c0, "Fuente", self.fonts)
        s0.pack(fill="x")
        grid0 = ttk.Frame(s0.body)
        grid0.pack(fill="x")
        grid0.columnconfigure((0, 1), weight=1)
        self._field(grid0, "q", "Q", "g/s", pos).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self._field(grid0, "h", "Hs", "m", pos).grid(row=0, column=1, sticky="ew")

        c1 = ttk.Frame(ribbon, padding=12)
        c1.grid(row=0, column=1, sticky="nsew")
        s1 = Section(c1, "Chimenea · Briggs", self.fonts)
        s1.pack(fill="x")
        grid1 = ttk.Frame(s1.body)
        grid1.pack(fill="x")
        for i in range(4):
            grid1.columnconfigure(i, weight=1)
        self._field(grid1, "d", "d", None, pos).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self._field(grid1, "vs", "vs", None, pos).grid(row=0, column=1, sticky="ew", padx=4)
        self._field(grid1, "Ts", "Ts", None, pos).grid(row=0, column=2, sticky="ew", padx=4)
        self._field(grid1, "Ta", "Ta", None).grid(row=0, column=3, sticky="ew", padx=(4, 0))

        c2 = ttk.Frame(ribbon, padding=12)
        c2.grid(row=0, column=2, sticky="nsew")
        s2 = Section(c2, "Meteorología", self.fonts)
        s2.pack(fill="x")
        grid2 = ttk.Frame(s2.body)
        grid2.pack(fill="x")
        grid2.columnconfigure(1, weight=2)
        self._field(grid2, "u", "u₁₀", "m/s", pos).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        cls_col = ttk.Frame(grid2)
        cls_col.grid(row=0, column=1, sticky="ew")
        ttk.Label(cls_col, text="Clase P-G", style="Soft.TLabel").pack(anchor="w")
        self.class_var = tk.StringVar(value=self.app.p.clase)
        ClassSegmented(cls_col, self.class_var, command=self._on_class_pick).pack(fill="x", pady=(4, 0))

        c3 = ttk.Frame(ribbon, padding=12)
        c3.grid(row=0, column=3, sticky="nsew")
        s3 = Section(c3, "Dominio", self.fonts)
        s3.pack(fill="x")
        grid3 = ttk.Frame(s3.body)
        grid3.pack(fill="x")
        grid3.columnconfigure((0, 1), weight=1)
        self._field(grid3, "max_dist", "X máx", "m", pos).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self._field(grid3, "trans_width", "Ancho Y", "m", pos).grid(row=0, column=1, sticky="ew")
        ttk.Button(c3, text="▶  Calcular", style="Primary.TButton",
                   command=self.app.recompute).pack(fill="x", pady=(10, 0))

        sep = tk.Frame(self.root, height=1, bg=COLORS["divider"])
        sep.grid(row=0, column=0, sticky="sew")

    # ------------------------------------------------------------------
    def _build_map_area(self) -> None:
        wrap = ttk.Frame(self.root, width=800, height=340)
        wrap.grid(row=1, column=0, sticky="nsew")
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)
        wrap.grid_propagate(False)

        self.fig = plot_style.new_figure(figsize=(13, 5.4))
        self.ax_contour = self.fig.add_subplot(111)
        self.fig.subplots_adjust(left=0.05, right=0.99, top=0.97, bottom=0.1)
        self.canvas = FigureCanvasTkAgg(self.fig, master=wrap)
        widget = self.canvas.get_tk_widget()
        widget.configure(bg=COLORS["bg"], highlightthickness=0)
        widget.grid(row=0, column=0, sticky="nsew")

        # ---- floating legend, top-left ----
        legend = ttk.Frame(wrap, padding=6)
        legend.place(relx=0.0, rely=0.0, x=14, y=12, anchor="nw")
        self.legend_var = tk.StringVar()
        ttk.Label(legend, textvariable=self.legend_var, style="Soft.TLabel").pack()

        # ---- floating results card, top-right ----
        card = BlueprintFrame(wrap)
        card.place(relx=1.0, rely=0.0, x=-18, y=16, anchor="ne", width=278)
        inner = ttk.Frame(card, padding=(13, 12))
        inner.pack(fill="both")
        self.res_title_var = tk.StringVar()
        ttk.Label(inner, textvariable=self.res_title_var, style="Section.TLabel").pack(anchor="w", pady=(0, 9))

        row1 = ttk.Frame(inner)
        row1.pack(fill="x")
        ttk.Label(row1, text="C MÁX", style="Faint.TLabel").pack(anchor="w")
        cmax_row = ttk.Frame(inner)
        cmax_row.pack(anchor="w", fill="x")
        self.cmax_var = tk.StringVar(value="--")
        tk.Label(cmax_row, textvariable=self.cmax_var, font=self.fonts.spec_n,
                 bg=COLORS["bg"], fg=COLORS["accent_900"]).pack(side="left")
        ttk.Label(cmax_row, text=" μg/m³", style="Faint.TLabel").pack(side="left", anchor="s", pady=(0, 3))

        row2 = ttk.Frame(inner, padding=(0, 8, 0, 0))
        row2.pack(fill="x")
        self.xmax_var = tk.StringVar(value="--")
        self.hfinal_var = tk.StringVar(value="--")
        for label, var in [("X EN C MÁX", self.xmax_var), ("H EFECTIVA", self.hfinal_var)]:
            cell = ttk.Frame(row2)
            cell.pack(side="left", padx=(0, 16))
            ttk.Label(cell, text=label, style="Faint.TLabel").pack(anchor="w")
            ttk.Label(cell, textvariable=var, style="Heading.TLabel").pack(anchor="w")

        sep = tk.Frame(inner, height=1, bg=COLORS["divider"])
        sep.pack(fill="x", pady=(9, 6))
        self.chain_var = tk.StringVar()
        ttk.Label(inner, textvariable=self.chain_var, style="Mono.TLabel", justify="left").pack(anchor="w")

        # ---- floating point inspector, bottom-left ----
        self.inspector = tk.Frame(wrap, bg=COLORS["accent_900"], highlightthickness=1,
                                   highlightbackground="#4a5c6d")
        inner2 = ttk.Frame(self.inspector, padding=(12, 10), style="Dark.TFrame")
        inner2.pack(fill="both")
        ttk.Label(inner2, text="INSPECTOR DE PUNTO", style="DarkSoft.TLabel").pack(anchor="w", pady=(0, 8))
        row = ttk.Frame(inner2, style="Dark.TFrame")
        row.pack(fill="x")
        self.pt_x, self.pt_y, self.pt_z = tk.StringVar(value="2400"), tk.StringVar(value="0"), tk.StringVar(value="0")
        for label, var in [("x", self.pt_x), ("y", self.pt_y), ("z", self.pt_z)]:
            cell = ttk.Frame(row, style="Dark.TFrame")
            cell.pack(side="left", padx=(0, 6))
            ttk.Label(cell, text=label, style="DarkSoft.TLabel").pack(anchor="w")
            ttk.Entry(cell, textvariable=var, style="Dark.TEntry", width=7).pack()
        ttk.Button(inner2, text="Calcular", style="Primary.TButton",
                   command=self._calc_point).pack(fill="x", pady=(8, 0))
        res_row = ttk.Frame(inner2, style="Dark.TFrame")
        res_row.pack(anchor="w", fill="x", pady=(9, 0))
        self.pt_val_var = tk.StringVar(value="—")
        tk.Label(res_row, textvariable=self.pt_val_var, font=self.fonts.spec_n,
                 bg=COLORS["accent_900"], fg=COLORS["bg"]).pack(side="left")
        ttk.Label(res_row, text=" μg/m³", style="DarkSoft.TLabel").pack(side="left", anchor="s", pady=(0, 3))
        self.pt_detail_var = tk.StringVar(value="")
        ttk.Label(inner2, textvariable=self.pt_detail_var, style="DarkSoft.TLabel").pack(anchor="w", pady=(4, 0))
        self.inspector.place_forget()

    def _calc_point(self) -> None:
        try:
            x, y, z = float(self.pt_x.get()), float(self.pt_y.get()), float(self.pt_z.get())
        except ValueError:
            self.pt_val_var.set("⚠")
            return
        self.app.calc_point(x, y, z)

    def show_point_result(self, x, y, z, r: dict) -> None:
        # The point may come from elsewhere (workbench step 4, the dialog),
        # so keep the inspector's own inputs in step with what it reports.
        self.pt_x.set(f"{x:g}")
        self.pt_y.set(f"{y:g}")
        self.pt_z.set(f"{z:g}")
        self.pt_val_var.set(f"{r['c']:.2f}")
        self.pt_detail_var.set(f"σy {r['sigma_y']:.0f} m · σz {r['sigma_z']:.0f} m · H {r['h']:.1f} m")
        self.inspector.place(relx=0.0, rely=1.0, x=18, y=-18, anchor="sw", width=256)

    def _on_class_pick(self) -> None:
        self.app.dominant_enabled = False
        self.app.p.clase = self.class_var.get()
        self.app.recompute()

    def _sync_briggs_enabled(self) -> None:
        enabled = self.app.use_auto_H_var.get()
        for key in ("d", "vs", "Ts", "Ta"):
            self.fields[key].set_enabled(enabled)

    def _on_briggs_toggle(self) -> None:
        self._sync_briggs_enabled()
        self.app.recompute()

    # ------------------------------------------------------------------
    def _build_bottom_strip(self) -> None:
        strip = ttk.Frame(self.root)
        strip.grid(row=2, column=0, sticky="ew")
        strip.columnconfigure(0, weight=1)
        sep = tk.Frame(self.root, height=1, bg=COLORS["divider"])
        sep.grid(row=2, column=0, sticky="new")

        left = ttk.Frame(strip, padding=(16, 14))
        left.grid(row=0, column=0, sticky="ew")
        ttk.Label(left, text="PERFIL Y = 0", style="Section.TLabel").pack(anchor="w", pady=(0, 6))
        panel = BlueprintFrame(left, height=150)
        panel.pack(fill="x")
        panel.pack_propagate(False)
        self.fig_line = plot_style.new_figure(figsize=(9, 1.6))
        self.ax_line = self.fig_line.add_subplot(111)
        self.fig_line.subplots_adjust(left=0.06, right=0.99, top=0.96, bottom=0.26)
        self.canvas_line = FigureCanvasTkAgg(self.fig_line, master=panel)
        self.canvas_line.get_tk_widget().configure(bg=COLORS["bg"], highlightthickness=0)
        self.canvas_line.get_tk_widget().pack(fill="x", padx=1, pady=1)

        right = ttk.Frame(strip, padding=(16, 14), width=330)
        right.grid(row=0, column=1, sticky="ns")
        right.grid_propagate(False)
        ttk.Label(right, text="FRECUENCIAS POR CLASE · SERIE 24 H", style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        bars = ttk.Frame(right)
        bars.pack(fill="x")
        self.freq_bar_vars = {}
        for c in "ABCDEF":
            col = ttk.Frame(bars)
            col.pack(side="left", expand=True, fill="x")
            bar = tk.Frame(col, bg=COLORS["accent_300"], height=8, width=18)
            bar.pack(side="bottom")
            ttk.Label(col, text=c, style="Mono.TLabel").pack(side="bottom", pady=(4, 0))
            self.freq_bar_vars[c] = bar
        self.freq_note_var = tk.StringVar(value="Sin datos de serie cargados — se usa clase D.")
        ttk.Label(right, textvariable=self.freq_note_var, style="Soft.TLabel", wraplength=300, justify="left"
                  ).pack(anchor="w", pady=(10, 0))

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        r = self.app.result
        if r is None:
            return
        point = None
        if self.app.last_point is not None:
            point = (self.app.last_point["x"], self.app.last_point["y"])
        plot_style.draw_contour(self.ax_contour, r, point=point)
        self.canvas.draw_idle()
        plot_style.draw_line(self.ax_line, r)
        self.canvas_line.draw_idle()

        self.res_title_var.set(f"RESULTADOS · CLASE {self.app.p.clase}")
        self.cmax_var.set(f"{r.cmax:.1f}")
        self.xmax_var.set(f"{r.xmax:.0f} m")
        self.hfinal_var.set(f"{r.H_final:.1f} m")
        self.chain_var.set(f"u₁₀ → u_eff   {self.app.p.u:.1f} → {r.u_eff:.2f} m/s\n"
                            f"p (clase {self.app.p.clase})     {r.p:.2f}\n"
                            f"Δh máx             {max(r.H_final - self.app.p.h, 0):.1f} m")
        self.legend_var.set(f"isopleta {self.app.iso_val:g} μg/m³")

        freqs = self.app.freqs_serie
        max_h = 40
        dom = max(freqs, key=freqs.get) if freqs else None
        for c in "ABCDEF":
            h = max(4, int(freqs.get(c, 0.0) * max_h)) if freqs else 4
            self.freq_bar_vars[c].configure(
                height=h, bg=COLORS["accent"] if c == dom else COLORS["accent_300"])
        if freqs:
            dom = max(freqs, key=freqs.get)
            self.freq_note_var.set(f"Dominante {dom} con {freqs[dom]:.3f} — es la clase usada si activas "
                                    "'clase dominante'.")
        else:
            self.freq_note_var.set("Sin datos de serie cargados — 'clase dominante' usaría D.")
