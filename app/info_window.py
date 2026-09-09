# -*- coding: utf-8 -*-
"""Technical help window. Same content as the original v4.0 app, laid out
with the Industry section styling and a scrollable body.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .theme import COLORS

BLOCKS = [
    ("Modelo de pluma gaussiana — descripción general", None,
     "Esta herramienta implementa el modelo de pluma gaussiana para una fuente puntual elevada, "
     "incorporando dispersión atmosférica por clase de estabilidad Pasquill-Gifford (A–F) y, "
     "opcionalmente, elevación de pluma según Briggs y corrección vertical de la velocidad del "
     "viento por ley exponencial."),

    ("Ecuación de concentración (estado estacionario, reflexión en el suelo)",
     "C(x,y,z) = Q / (2π·u·σy·σz)\n"
     "         · exp(−y²/(2σy²))\n"
     "         · [ exp(−(z−H)²/(2σz²)) + exp(−(z+H)²/(2σz²)) ]", None),

    ("Definición de variables", None,
     "Q   : tasa de emisión (g/s)\n"
     "u   : velocidad del viento efectiva (m/s)\n"
     "σy  : coeficiente de dispersión transversal (m)\n"
     "σz  : coeficiente de dispersión vertical (m)\n"
     "H   : altura efectiva de la fuente (m)\n"
     "x, y: coordenadas longitudinal y transversal (m)\n"
     "z   : altura del receptor (m)"),

    ("Clases de estabilidad atmosférica (Pasquill–Gifford)", None,
     "La estabilidad se define entre A (muy inestable) y F (muy estable). Esta condición controla "
     "la intensidad de la turbulencia atmosférica y determina la magnitud de σy(x) y σz(x). "
     "Se puede seleccionar una clase fija (A–F) o usar la clase dominante a partir de "
     "frecuencias cargadas manualmente o generadas con la serie demo de 24 h."),

    ("Altura efectiva — elevación de pluma (Briggs)", "H(x) = Hs + Δh(x)",
     "Hs es la altura geométrica de la chimenea y Δh(x) corresponde al ascenso por flotabilidad. "
     "El término Δh(x) depende del flujo de flotabilidad F y varía según el régimen de estabilidad:\n"
     "  · A–D (inestable / neutral): mayor mezcla y ascenso relativo.\n"
     "  · E–F (estable): la estratificación limita el ascenso y reduce la altura efectiva."),

    ("Corrección de velocidad del viento (ley exponencial)",
     "u(z) = u₁₀ · (z/10)^p\n"
     "u_eff = u₁₀ · (H_ref/10)^p",
     "La velocidad de entrada se interpreta como u₁₀ (medida a 10 m). El exponente p se asigna "
     "según la clase de estabilidad:\n"
     "  A: 0.15 · B: 0.15 · C: 0.20 · D: 0.25 · E: 0.40 · F: 0.60\n"
     "H_ref se toma como H_final cuando Briggs está activo, o como Hs en caso contrario."),

    ("Procedimiento de cálculo (esquema de dos etapas)", None,
     "1) Estimar H_ref usando inicialmente u = u₁₀.\n"
     "2) Calcular u_eff con H_ref y recalcular H(x) y C(x,y,z) usando u_eff.\n\n"
     "Este esquema mejora la coherencia física al considerar el incremento de velocidad con la "
     "altura, manteniendo una formulación operativa adecuada para análisis y enseñanza."),

    ("Limitaciones del modelo", None,
     "· Emisión continua y condiciones estacionarias.\n"
     "· Viento horizontal uniforme (sin cambio de dirección).\n"
     "· Terreno plano; no incluye edificios ni efectos topográficos.\n"
     "· No incluye deposición, química atmosférica ni lavado por lluvia.\n"
     "· No es representativo muy cerca de la fuente (zona de chorro)."),
]


def show_info_window(app) -> tk.Toplevel:
    win = tk.Toplevel(app)
    win.title("Información técnica — Modelo de pluma gaussiana")
    win.geometry("860x700")
    win.configure(background=COLORS["bg"])
    win.transient(app)
    win.bind("<Escape>", lambda _e: win.destroy())
    fonts = app.fonts

    bar = tk.Frame(win, bg=COLORS["accent_900"])
    bar.pack(fill="x")
    tk.Label(bar, text="Información técnica del modelo", font=fonts.titlebar,
             bg=COLORS["accent_900"], fg=COLORS["bg"]).pack(side="left", padx=14, pady=8)
    tk.Button(bar, text="✕  Cerrar", command=win.destroy, relief="flat", bd=0,
              font=fonts.body_soft, bg=COLORS["accent_900"], fg=COLORS["bg"],
              activebackground=COLORS["accent_800"], activeforeground=COLORS["bg"],
              highlightthickness=0, cursor="hand2").pack(side="right", padx=12)

    container = ttk.Frame(win)
    container.pack(fill="both", expand=True)
    canvas = tk.Canvas(container, highlightthickness=0, bg=COLORS["bg"])
    vscroll = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vscroll.set)
    canvas.pack(side="left", fill="both", expand=True)
    vscroll.pack(side="right", fill="y")

    content = ttk.Frame(canvas, padding=(24, 20))
    win_id = canvas.create_window((0, 0), window=content, anchor="nw")
    content.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))
    canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))
    win.bind("<Destroy>", lambda _e: canvas.unbind_all("<MouseWheel>"))

    for title, formula, text in BLOCKS:
        block = ttk.Frame(content)
        block.pack(fill="x", pady=(0, 22))
        ttk.Label(block, text=title.upper(), style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        tk.Frame(block, height=1, bg=COLORS["divider"]).pack(fill="x", pady=(0, 10))
        if formula:
            tk.Label(block, text=formula, font=fonts.mono, bg=COLORS["bg"],
                     fg=COLORS["accent_900"], justify="left").pack(anchor="w", pady=(0, 8))
        if text:
            ttk.Label(block, text=text, style="Soft.TLabel", wraplength=760,
                      justify="left").pack(anchor="w")

    return win
