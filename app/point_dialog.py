# -*- coding: utf-8 -*-
"""Point-calculation dialog (mockup 1d): C(x, y, z) at a single receptor,
with the intermediate values that produced it. The computed point is
marked on the map behind it.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .theme import COLORS
from .widgets import BlueprintFrame


class PointDialog(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.fonts = app.fonts
        self.title("Cálculo puntual de C(x, y, z)")
        self.configure(background=COLORS["bg"])
        self.transient(app)
        self.resizable(False, False)
        self.bind("<Escape>", lambda _e: self.destroy())

        bar = tk.Frame(self, bg=COLORS["accent_900"])
        bar.pack(fill="x")
        tk.Label(bar, text="Cálculo puntual", font=self.fonts.titlebar,
                 bg=COLORS["accent_900"], fg=COLORS["bg"]).pack(side="left", padx=12, pady=7)
        tk.Label(bar, text="Esc para cerrar", font=self.fonts.mono_soft,
                 bg=COLORS["accent_900"], fg=COLORS["accent_300"]).pack(side="right", padx=12)

        body = ttk.Frame(self, padding=(20, 18))
        body.pack(fill="both", expand=True)

        grid = ttk.Frame(body)
        grid.pack(fill="x")
        last = app.last_point
        self.vars = {
            "x": tk.StringVar(value=f"{last['x']:g}" if last else "2400"),
            "y": tk.StringVar(value=f"{last['y']:g}" if last else "0"),
            "z": tk.StringVar(value=f"{last['z']:g}" if last else "1.5"),
        }
        for i, (key, label) in enumerate([("x", "x"), ("y", "y"), ("z", "z receptor")]):
            grid.columnconfigure(i, weight=1)
            cell = ttk.Frame(grid)
            cell.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 11, 0))
            head = ttk.Frame(cell)
            head.pack(fill="x")
            ttk.Label(head, text=label, style="Soft.TLabel").pack(side="left")
            ttk.Label(head, text=" m", style="Faint.TLabel").pack(side="left")
            entry = ttk.Entry(cell, textvariable=self.vars[key], width=12)
            entry.pack(fill="x", pady=(4, 0))
            entry.bind("<Return>", lambda _e: self._calc())

        ttk.Button(body, text="▶  Calcular en este punto", style="Primary.TButton",
                   command=self._calc).pack(fill="x", pady=(14, 0))

        panel = BlueprintFrame(body)
        panel.pack(fill="x", pady=(20, 0))
        inner = ttk.Frame(panel, padding=16)
        inner.pack(fill="both")
        ttk.Label(inner, text="RESULTADO", style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        row = ttk.Frame(inner)
        row.pack(anchor="w", fill="x")
        self.value_var = tk.StringVar(value="—")
        tk.Label(row, textvariable=self.value_var, font=self.fonts.spec_n_lg,
                 bg=COLORS["bg"], fg=COLORS["accent_900"]).pack(side="left")
        ttk.Label(row, text=" μg/m³", style="Faint.TLabel").pack(side="left", anchor="s", pady=(0, 5))

        self.detail_vars = {}
        detail = ttk.Frame(inner)
        detail.pack(fill="x", pady=(12, 0))
        for key, label in [("ueff", "u_eff"), ("h", "H_eff en x"), ("sigmas", "σy · σz")]:
            line = ttk.Frame(detail)
            line.pack(fill="x", pady=2)
            ttk.Label(line, text=label, style="Mono.TLabel").pack(side="left")
            var = tk.StringVar(value="—")
            ttk.Label(line, textvariable=var, style="Mono.TLabel").pack(side="right")
            self.detail_vars[key] = var

        self.note_var = tk.StringVar()
        ttk.Label(body, textvariable=self.note_var, style="Faint.TLabel",
                  wraplength=400, justify="left").pack(anchor="w", pady=(12, 0))
        self._set_note()

        if last:
            self._show(last)

    def _set_note(self) -> None:
        p = self.app.p
        briggs = "Briggs activo" if p.use_auto_H else "Briggs desactivado (H = Hs)"
        wind = "corrección de viento activa" if p.use_wind_correction else "sin corrección de viento"
        self.note_var.set(f"Clase {p.clase} · {briggs} · {wind}. El punto queda marcado en el mapa.")

    def _calc(self) -> None:
        try:
            x = float(self.vars["x"].get())
            y = float(self.vars["y"].get() or 0.0)
            z = float(self.vars["z"].get())
        except ValueError:
            self.value_var.set("⚠")
            self.note_var.set("Revisa los valores de x, y, z: deben ser números.")
            return
        r = self.app.calc_point(x, y, z)
        self._show(r)
        self._set_note()

    def _show(self, r: dict) -> None:
        self.value_var.set(f"{r['c']:.4f}")
        self.detail_vars["ueff"].set(f"{r['u_eff']:.3f} m/s")
        self.detail_vars["h"].set(f"{r['h']:.2f} m")
        self.detail_vars["sigmas"].set(f"{r['sigma_y']:.0f} · {r['sigma_z']:.0f} m")
