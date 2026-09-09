# -*- coding: utf-8 -*-
""""Modo estudio" (mockup 1c): one decision per screen, the physics
explained in plain language, and a live preview of what the choice does
to the plume. Aimed at students meeting dispersion modeling for the
first time; on finishing it hands its case back to the workbench.
"""

from __future__ import annotations

import copy
import tkinter as tk
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from . import model, plot_style
from .theme import COLORS
from .widgets import BlueprintFrame, HorizontalStepTracker, ValidatedField

STEP_LABELS = ["Fuente", "Estabilidad atmosférica", "Dominio", "Resultados"]

CLASS_TAGS = {
    "A": "MUY INEST.", "B": "INEST.", "C": "LIG. INEST.",
    "D": "NEUTRA", "E": "ESTABLE", "F": "MUY EST.",
}

SIGMA_TEXT = {
    "A": "σy = 0.22·x·(1+10⁻⁴x)^-0.5\nσz = 0.20·x",
    "B": "σy = 0.16·x·(1+10⁻⁴x)^-0.5\nσz = 0.12·x",
    "C": "σy = 0.11·x·(1+10⁻⁴x)^-0.5\nσz = 0.08·x·(1+2·10⁻⁴x)^-0.5",
    "D": "σy = 0.08·x·(1+10⁻⁴x)^-0.5\nσz = 0.06·x·(1+1.5·10⁻³x)^-0.5",
    "E": "σy = 0.06·x·(1+10⁻⁴x)^-0.5\nσz = 0.03·x·(1+3·10⁻⁴x)^-1",
    "F": "σy = 0.04·x·(1+10⁻⁴x)^-0.5\nσz = 0.016·x·(1+3·10⁻⁴x)^-1",
}

EFFECT_TEXT = {
    "A": "Pluma ancha y de rápido crecimiento vertical: toca el suelo pronto, con un máximo alto y cercano a la chimenea.",
    "B": "Mezcla intensa: la pluma se abre rápido y el máximo aparece cerca de la fuente.",
    "C": "Mezcla moderada: el máximo se aleja algo de la chimenea y baja respecto a las clases inestables.",
    "D": "Caso neutro de referencia: crecimiento equilibrado de σy y σz, máximo a distancia intermedia.",
    "E": "Estratificación estable: la pluma se ensancha poco, tarda en tocar el suelo y el máximo se aleja.",
    "F": "Muy estable: pluma estrecha y persistente; el máximo aparece lejos y el ascenso de Briggs queda limitado.",
}


class StudyWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.fonts = app.fonts
        self.title("Modelo Gaussiano de Pluma — Modo estudio")
        self.geometry("980x680")
        self.configure(background=COLORS["bg"])
        self.transient(app)
        self.bind("<Escape>", lambda _e: self.destroy())

        # A private copy of the case, so exploring here never disturbs the
        # workbench until the student chooses to apply it.
        self.p = copy.copy(app.p)
        self.index = 0
        self._preview_job = None

        self.tracker = HorizontalStepTracker(self, STEP_LABELS, self.fonts)
        self.tracker.pack(fill="x")
        tk.Frame(self, height=1, bg=COLORS["divider"]).pack(fill="x")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        self.content = ttk.Frame(body, padding=(24, 22))
        self.content.grid(row=0, column=0, sticky="nsew")
        tk.Frame(body, width=1, bg=COLORS["divider"]).grid(row=0, column=1, sticky="ns")
        self._build_preview(body)

        self.show_step(0)

    # ------------------------------------------------------------------
    # Live preview column
    # ------------------------------------------------------------------

    def _build_preview(self, parent) -> None:
        col = tk.Frame(parent, bg=COLORS["neutral_100"], width=330)
        col.grid(row=0, column=2, sticky="ns")
        col.grid_propagate(False)

        inner = ttk.Frame(col, padding=(20, 22), style="Neutral.TFrame")
        inner.pack(fill="both", expand=True)
        ttk.Label(inner, text="VISTA PREVIA EN VIVO", style="Section.TLabel").pack(anchor="w", pady=(0, 10))

        panel = BlueprintFrame(inner, bg=COLORS["bg"])
        panel.pack(fill="x")
        self.fig = plot_style.new_figure(figsize=(3.1, 2.0))
        self.ax = self.fig.add_subplot(111)
        self.fig.subplots_adjust(left=0.02, right=0.98, top=0.97, bottom=0.06)
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.canvas = FigureCanvasTkAgg(self.fig, master=panel)
        self.canvas.get_tk_widget().configure(bg=COLORS["bg"], highlightthickness=0)
        self.canvas.get_tk_widget().pack(fill="x", padx=1, pady=1)

        axis = ttk.Frame(inner)
        axis.pack(fill="x", pady=(5, 16))
        self.axis_var = tk.StringVar()
        ttk.Label(axis, textvariable=self.axis_var, style="Faint.TLabel").pack(side="left")

        self.readouts = {}
        for key, label, unit in [("cmax", "C máx", "μg/m³"), ("xmax", "x en C máx", "m"),
                                  ("hfinal", "H efectiva", "m")]:
            row = ttk.Frame(inner)
            row.pack(fill="x", pady=(0, 9))
            ttk.Label(row, text=label, style="Soft.TLabel").pack(side="left")
            var = tk.StringVar(value="—")
            ttk.Label(row, text=unit, style="Faint.TLabel").pack(side="right", anchor="s")
            tk.Label(row, textvariable=var, font=self.fonts.heading,
                     bg=COLORS["neutral_100"], fg=COLORS["accent_900"]).pack(side="right", padx=(0, 5))
            self.readouts[key] = var
            tk.Frame(inner, height=1, bg=COLORS["divider"]).pack(fill="x", pady=(0, 9))

        compare = tk.Frame(inner, bg=COLORS["bg"], highlightthickness=0)
        compare.pack(fill="x", pady=(6, 0))
        tk.Frame(compare, width=2, bg=COLORS["accent"]).pack(side="left", fill="y")
        cbody = ttk.Frame(compare, padding=(11, 10))
        cbody.pack(side="left", fill="both", expand=True)
        ttk.Label(cbody, text="COMPARADO CON D (NEUTRA)", style="Section.TLabel").pack(anchor="w", pady=(0, 4))
        self.compare_var = tk.StringVar(value="—")
        ttk.Label(cbody, textvariable=self.compare_var, style="Soft.TLabel",
                  wraplength=240, justify="left").pack(anchor="w")

    def _refresh_preview(self) -> None:
        """Recompute the preview on a coarse grid, debounced so dragging
        through the class cards stays responsive."""
        if self._preview_job is not None:
            self.after_cancel(self._preview_job)
        self._preview_job = self.after(60, self._do_refresh_preview)

    def _do_refresh_preview(self) -> None:
        self._preview_job = None
        r = model.compute(self.p, self.app.iso_val, nx=140)
        plot_style.draw_contour(self.ax, r)
        self.ax.set_xlabel("")
        self.ax.set_ylabel("")
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.canvas.draw_idle()

        self.readouts["cmax"].set(f"{r.cmax:.1f}")
        self.readouts["xmax"].set(f"{r.xmax:.0f}")
        self.readouts["hfinal"].set(f"{r.H_final:.1f}")
        self.axis_var.set(f"0 — {self.p.max_dist:g} m")

        if self.p.clase == "D":
            self.compare_var.set("Ésta es la referencia neutra con la que se comparan las demás clases.")
        else:
            neutral = copy.copy(self.p)
            neutral.clase = "D"
            rd = model.compute(neutral, self.app.iso_val, nx=140)
            verb_c = "sube" if r.cmax >= rd.cmax else "baja"
            verb_x = "se acerca" if r.xmax <= rd.xmax else "se aleja"
            self.compare_var.set(
                f"El máximo {verb_c} de {rd.cmax:.1f} a {r.cmax:.1f} μg/m³ y {verb_x} de "
                f"{rd.xmax:.0f} a {r.xmax:.0f} m."
            )

    # ------------------------------------------------------------------
    # Steps
    # ------------------------------------------------------------------

    def show_step(self, index: int) -> None:
        self.index = index
        self.tracker.set_active(index)
        for child in self.content.winfo_children():
            child.destroy()

        ttk.Label(self.content, text=f"PASO {index + 1} DE {len(STEP_LABELS)}",
                  style="Section.TLabel").pack(anchor="w", pady=(0, 6))
        builder = [self._step_fuente, self._step_estabilidad, self._step_dominio, self._step_resultados][index]
        builder()
        self._build_nav()
        self._refresh_preview()

    def _heading(self, title: str, text: str) -> None:
        tk.Label(self.content, text=title, font=self.fonts.heading_lg,
                 bg=COLORS["bg"], fg=COLORS["text"], justify="left", anchor="w").pack(anchor="w", pady=(0, 8))
        ttk.Label(self.content, text=text, style="Soft.TLabel", wraplength=470,
                  justify="left").pack(anchor="w", pady=(0, 18))

    def _study_field(self, parent, key, label, unit, rule=None):
        f = ValidatedField(parent, label, unit, getattr(self.p, key), self.fonts, rule=rule,
                            on_commit=lambda k=key: self._commit(k), width=12)
        f._key = key
        self._fields[key] = f
        return f

    def _commit(self, key: str) -> None:
        setattr(self.p, key, self._fields[key].value)
        self._refresh_preview()

    def _step_fuente(self) -> None:
        self._fields = {}
        self._heading("¿Qué emite la chimenea y con qué fuerza?",
                       "La tasa de emisión Q fija la escala de todas las concentraciones: al duplicarla, todo el "
                       "campo se duplica. La altura Hs y las condiciones de salida (diámetro, velocidad y "
                       "temperatura de los gases) deciden a qué altura viaja realmente la pluma.")
        pos = lambda v: (v > 0, "Debe ser mayor que 0.")
        grid = ttk.Frame(self.content)
        grid.pack(fill="x")
        grid.columnconfigure((0, 1, 2), weight=1)
        specs = [("q", "Q — Emisión", "g/s"), ("h", "Hs — Chimenea", "m"), ("d", "d — Diámetro", "m"),
                 ("vs", "vs — Salida", "m/s"), ("Ts", "Ts — Gases", "K"), ("Ta", "Ta — Ambiente", "K")]
        for i, (key, label, unit) in enumerate(specs):
            r, c = divmod(i, 3)
            self._study_field(grid, key, label, unit, pos if key != "Ta" else None).grid(
                row=r, column=c, sticky="ew", padx=(0 if c == 0 else 10, 0), pady=(0, 12))
        self._info_box("Lo que se calcula con estos valores",
                        "F = g·vs·d²·(Ts−Ta) / (4·Ts)\nΔh(x) = 1.6·F^(1/3)·x^(2/3) / u",
                        "El flujo de flotabilidad F mide cuánta energía térmica empuja la pluma hacia arriba; "
                        "de él sale el ascenso Δh que se suma a la altura de chimenea.")

    def _step_estabilidad(self) -> None:
        self._heading("¿Qué tan turbulenta está la atmósfera?",
                       "La clase de Pasquill-Gifford resume la turbulencia en una letra, de A (muy inestable, "
                       "mediodía soleado y viento flojo) a F (muy estable, noche despejada). Es la decisión que "
                       "más mueve el resultado: fija σy(x) y σz(x), y con ellos el ancho de la pluma.")

        cards = ttk.Frame(self.content)
        cards.pack(fill="x", pady=(0, 8))
        self._class_cards = {}
        for i, c in enumerate("ABCDEF"):
            cards.columnconfigure(i, weight=1)
            card = tk.Frame(cards, bg=COLORS["bg"], highlightthickness=1,
                             highlightbackground=COLORS["divider"], cursor="hand2")
            card.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 7, 0))
            letter = tk.Label(card, text=c, font=self.fonts.heading_lg, bg=COLORS["bg"], fg=COLORS["text"])
            letter.pack(pady=(9, 0))
            tag = tk.Label(card, text=CLASS_TAGS[c], font=self.fonts.mono_soft,
                            bg=COLORS["bg"], fg=COLORS["text_faint"])
            tag.pack(pady=(3, 9))
            for w in (card, letter, tag):
                w.bind("<Button-1>", lambda _e, cl=c: self._pick_class(cl))
            self._class_cards[c] = (card, letter, tag)

        ttk.Label(self.content, text="O deja que la app la deduzca de una serie horaria — "
                                      "menú Serie ▸ Generar serie demo de 24 h",
                  style="Faint.TLabel", wraplength=560, justify="left").pack(anchor="w", pady=(0, 18))

        self._effect_box = ttk.Frame(self.content)
        self._effect_box.pack(fill="x")
        self._paint_class_cards()

    def _pick_class(self, clase: str) -> None:
        self.p.clase = clase
        self._paint_class_cards()
        self._refresh_preview()

    def _paint_class_cards(self) -> None:
        for c, (card, letter, tag) in self._class_cards.items():
            active = c == self.p.clase
            bg = COLORS["accent"] if active else COLORS["bg"]
            card.configure(bg=bg, highlightbackground=COLORS["accent"] if active else COLORS["divider"])
            letter.configure(bg=bg, fg=COLORS["bg"] if active else COLORS["text"])
            tag.configure(bg=bg, fg=COLORS["bg"] if active else COLORS["text_faint"])

        for child in self._effect_box.winfo_children():
            child.destroy()
        from .physics import WIND_EXPONENT_P
        cl = self.p.clase
        p = WIND_EXPONENT_P[cl]
        self._info_box(f"Lo que cambia al elegir {cl}",
                        f"{SIGMA_TEXT[cl]}\np = {p:.2f}  →  u_eff = u₁₀·(H/10)^{p:.2f}",
                        EFFECT_TEXT[cl], parent=self._effect_box)

    def _step_dominio(self) -> None:
        self._fields = {}
        self._heading("¿Qué parte del terreno quieres mirar?",
                       "El dominio no cambia la física: recorta la ventana de cálculo. Conviene que llegue más "
                       "allá del máximo para no cortarlo, y que el ancho cubra la apertura lateral de la pluma. "
                       "La altura del receptor z es dónde se evalúa la concentración: 0 m es el nivel del suelo, "
                       "1.5 m aproxima la altura de respiración.")
        pos = lambda v: (v > 0, "Debe ser mayor que 0.")
        grid = ttk.Frame(self.content)
        grid.pack(fill="x")
        grid.columnconfigure((0, 1, 2), weight=1)
        self._study_field(grid, "max_dist", "X máx", "m", pos).grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self._study_field(grid, "trans_width", "Ancho Y", "m", pos).grid(row=0, column=1, sticky="ew", padx=(0, 10))
        self._study_field(grid, "z_rec", "z receptor", "m",
                           lambda v: (v >= 0, "Debe ser ≥ 0.")).grid(row=0, column=2, sticky="ew")
        self._info_box("Reflexión en el suelo",
                        "C(x,y,z) ∝ exp(−(z−H)²/2σz²) + exp(−(z+H)²/2σz²)",
                        "El segundo término es la imagen especular de la pluma bajo el suelo: representa el "
                        "material que llega al terreno y rebota en lugar de depositarse.")

    def _step_resultados(self) -> None:
        r = model.compute(self.p, self.app.iso_val, nx=200)
        self._heading("Esto es lo que predice el modelo",
                       "Con la fuente, la estabilidad y el dominio ya elegidos, el modelo resuelve la ecuación "
                       "gaussiana en toda la malla. Revisa el máximo y a qué distancia cae: es el par de números "
                       "que resume el caso.")
        grid = ttk.Frame(self.content)
        grid.pack(fill="x", pady=(0, 18))
        rows = [("C máx", f"{r.cmax:.2f}", "μg/m³"), ("x en C máx", f"{r.xmax:.0f}", "m"),
                ("H efectiva", f"{r.H_final:.1f}", "m"), ("u efectivo", f"{r.u_eff:.2f}", "m/s")]
        for i, (label, value, unit) in enumerate(rows):
            grid.columnconfigure(i, weight=1)
            cell = ttk.Frame(grid)
            cell.grid(row=0, column=i, sticky="ew")
            ttk.Label(cell, text=label.upper(), style="Faint.TLabel").pack(anchor="w")
            vrow = ttk.Frame(cell)
            vrow.pack(anchor="w")
            tk.Label(vrow, text=value, font=self.fonts.spec_n, bg=COLORS["bg"],
                     fg=COLORS["accent_900"]).pack(side="left")
            ttk.Label(vrow, text=" " + unit, style="Faint.TLabel").pack(side="left", anchor="s", pady=(0, 3))

        self._info_box("Cómo se llegó hasta aquí",
                        f"clase {self.p.clase} · p = {r.p:.2f} · F = {r.F:.1f} m⁴/s³\n"
                        f"u₁₀ = {self.p.u:g} m/s  →  u_eff = {r.u_eff:.2f} m/s\n"
                        f"H = Hs + Δh = {self.p.h:g} + {max(r.H_final - self.p.h, 0):.1f} = {r.H_final:.1f} m",
                        "Al aplicar el caso, el banco de trabajo recalcula con la malla completa y podrás "
                        "explorar puntos concretos, isopletas y exportaciones.")

    def _info_box(self, title: str, formula: str, text: str, parent=None) -> None:
        parent = parent or self.content
        box = tk.Frame(parent, bg=COLORS["accent_100"], highlightthickness=1,
                        highlightbackground=COLORS["divider"])
        box.pack(fill="x")
        inner = tk.Frame(box, bg=COLORS["accent_100"])
        inner.pack(fill="x", padx=16, pady=14)
        tk.Label(inner, text=title.upper(), font=self.fonts.section, bg=COLORS["accent_100"],
                 fg=COLORS["accent_800"]).pack(anchor="w", pady=(0, 7))
        tk.Label(inner, text=formula, font=self.fonts.mono, bg=COLORS["accent_100"],
                 fg=COLORS["accent_900"], justify="left").pack(anchor="w")
        tk.Label(inner, text=text, font=self.fonts.body_soft, bg=COLORS["accent_100"],
                 fg=COLORS["accent_900"], wraplength=460, justify="left").pack(anchor="w", pady=(9, 0))

    # ------------------------------------------------------------------
    def _build_nav(self) -> None:
        nav = ttk.Frame(self.content)
        nav.pack(fill="x", side="bottom", pady=(22, 0))
        if self.index > 0:
            ttk.Button(nav, text="Atrás", style="Secondary.TButton",
                       command=lambda: self.show_step(self.index - 1)).pack(side="left", padx=(0, 9))
        if self.index < len(STEP_LABELS) - 1:
            ttk.Button(nav, text="Continuar", style="Primary.TButton",
                       command=lambda: self.show_step(self.index + 1)).pack(side="left")
            skip = ttk.Label(nav, text="Cálculo listo · saltar al resultado", style="Faint.TLabel",
                             cursor="hand2")
            skip.pack(side="right")
            skip.bind("<Button-1>", lambda _e: self.show_step(len(STEP_LABELS) - 1))
        else:
            ttk.Button(nav, text="Aplicar al banco de trabajo", style="Primary.TButton",
                       command=self._apply).pack(side="left")

    def _apply(self) -> None:
        self.app.p = copy.copy(self.p)
        self.app.dominant_enabled = False
        self.app.use_auto_H_var.set(self.p.use_auto_H)
        self.app.use_wind_var.set(self.p.use_wind_correction)
        self.app._build_view(self.app.view_mode_var.get())
        self.app.recompute()
        self.destroy()
