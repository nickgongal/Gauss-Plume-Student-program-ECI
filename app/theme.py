# -*- coding: utf-8 -*-
"""Ttk theme port of the "Industry" blueprint/steel design system
(project/industry.css) — flat, square-cornered, technical-drawing look:
dark steel-blue chrome, one accent blue, monospace numeric accents,
condensed headings.
"""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

COLORS = {
    "bg": "#f2f2f3",
    "surface": "#e9e9ea",
    "text": "#1d1f20",
    "text_soft": "#5a5c5e",
    "text_faint": "#8d8e90",
    "divider": "#d6d6d8",
    "accent": "#5980a6",
    "accent_100": "#eef6ff",
    "accent_300": "#b5d9fd",
    "accent_700": "#416180",
    "accent_800": "#2c455d",
    "accent_900": "#1d2d3d",
    "neutral_100": "#f5f5f8",
    "neutral_200": "#e7e7ea",
    "error_bg": "#fbecec",
    "error_border": "#a33a3a",
    "error_text": "#8a2f2f",
    "error_text_soft": "#7a2b2b",
    "canvas_bg": "#e4e4e6",
}

# The plume-map ramp: low (near-white/green) -> high (red = C max).
RAMP_STOPS = [
    (0.00, (242, 242, 243)),
    (0.12, (225, 236, 214)),
    (0.30, (150, 190, 120)),
    (0.50, (214, 206, 110)),
    (0.70, (224, 158, 66)),
    (0.86, (199, 92, 45)),
    (1.00, (168, 32, 32)),
]

def ramp_rgb(t: float) -> tuple[int, int, int]:
    """Interpolate the plume-map color ramp at t in [0, 1]."""
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    stops = RAMP_STOPS
    for i in range(1, len(stops)):
        t1, c1 = stops[i]
        if t <= t1 or i == len(stops) - 1:
            t0, c0 = stops[i - 1]
            f = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            return tuple(int(round(c0[k] + (c1[k] - c0[k]) * f)) for k in range(3))
    return stops[-1][1]


MONO_FAMILIES = ["Menlo", "Consolas", "DejaVu Sans Mono", "Courier New"]
HEADING_FAMILIES = ["Barlow Condensed", "Oswald", "Arial Narrow", "Segoe UI", "Helvetica"]
BODY_FAMILIES = ["Barlow", "Segoe UI", "Helvetica", "Arial"]


def _pick_family(preferred: list[str]) -> str:
    available = set(tkfont.families())
    for name in preferred:
        if name in available:
            return name
    return preferred[-1]


class Fonts:
    def __init__(self, root: tk.Misc):
        heading_fam = _pick_family(HEADING_FAMILIES)
        body_fam = _pick_family(BODY_FAMILIES)
        mono_fam = _pick_family(MONO_FAMILIES)

        self.body = tkfont.Font(root, family=body_fam, size=10)
        self.body_soft = tkfont.Font(root, family=body_fam, size=9)
        self.label = tkfont.Font(root, family=body_fam, size=9)
        self.section = tkfont.Font(root, family=heading_fam, size=9, weight="bold")
        self.heading = tkfont.Font(root, family=heading_fam, size=12, weight="bold")
        self.heading_lg = tkfont.Font(root, family=heading_fam, size=16, weight="bold")
        self.spec_n = tkfont.Font(root, family=heading_fam, size=22, weight="bold")
        self.spec_n_lg = tkfont.Font(root, family=heading_fam, size=30, weight="bold")
        self.spec_u = tkfont.Font(root, family=body_fam, size=8)
        self.badge = tkfont.Font(root, family=heading_fam, size=30, weight="bold")
        self.mono = tkfont.Font(root, family=mono_fam, size=9)
        self.mono_soft = tkfont.Font(root, family=mono_fam, size=8)
        self.titlebar = tkfont.Font(root, family=heading_fam, size=11, weight="bold")


def apply_theme(root: tk.Misc) -> tuple[ttk.Style, Fonts]:
    fonts = Fonts(root)
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    c = COLORS
    root.configure(background=c["canvas_bg"])

    style.configure(".", background=c["bg"], foreground=c["text"], font=fonts.body)
    style.configure("TFrame", background=c["bg"])
    style.configure("Surface.TFrame", background=c["surface"])
    style.configure("Neutral.TFrame", background=c["neutral_100"])
    style.configure("Dark.TFrame", background=c["accent_900"])

    style.configure("TLabel", background=c["bg"], foreground=c["text"], font=fonts.body)
    style.configure("Soft.TLabel", background=c["bg"], foreground=c["text_soft"], font=fonts.body_soft)
    style.configure("Faint.TLabel", background=c["bg"], foreground=c["text_faint"], font=fonts.mono_soft)
    style.configure("Section.TLabel", background=c["bg"], foreground=c["text_soft"], font=fonts.section)
    style.configure("Heading.TLabel", background=c["bg"], foreground=c["text"], font=fonts.heading)
    style.configure("Mono.TLabel", background=c["bg"], foreground=c["text_soft"], font=fonts.mono)
    style.configure("Accent.TLabel", background=c["bg"], foreground=c["accent_800"], font=fonts.body)
    style.configure("Dark.TLabel", background=c["accent_900"], foreground=c["bg"], font=fonts.body)
    style.configure("DarkSoft.TLabel", background=c["accent_900"], foreground=c["accent_300"], font=fonts.mono_soft)
    style.configure("Error.TLabel", background=c["bg"], foreground=c["error_text"], font=fonts.body_soft)
    style.configure("ErrorBanner.TLabel", background=c["error_bg"], foreground=c["error_text_soft"], font=fonts.body_soft)
    style.configure("WarnBanner.TLabel", background=c["accent_100"], foreground=c["accent_900"], font=fonts.body_soft)

    # ---- Entries ----
    style.configure(
        "TEntry", fieldbackground=c["surface"], foreground=c["text"],
        bordercolor=c["divider"], lightcolor=c["divider"], darkcolor=c["divider"],
        insertcolor=c["text"], padding=5, relief="flat",
    )
    style.map(
        "TEntry",
        fieldbackground=[("disabled", "#e3e3e4")],
        foreground=[("disabled", c["text_faint"])],
    )
    style.configure(
        "Valid.TEntry", fieldbackground=c["surface"],
        bordercolor=c["accent"], lightcolor=c["accent"], darkcolor=c["accent"],
        padding=5, relief="flat",
    )
    style.configure(
        "Error.TEntry", fieldbackground=c["error_bg"],
        bordercolor=c["error_border"], lightcolor=c["error_border"], darkcolor=c["error_border"],
        padding=5, relief="flat",
    )
    style.configure(
        "Dark.TEntry", fieldbackground="#28394a", foreground=c["bg"],
        bordercolor="#4a5c6d", lightcolor="#4a5c6d", darkcolor="#4a5c6d",
        insertcolor=c["bg"], padding=5, relief="flat",
    )

    # ---- Buttons ----
    style.configure(
        "Primary.TButton", background=c["accent"], foreground=c["bg"],
        font=fonts.section, padding=(12, 8), relief="flat", borderwidth=0,
    )
    style.map(
        "Primary.TButton",
        background=[("pressed", c["accent_900"]), ("active", c["accent_700"]), ("disabled", c["divider"])],
        foreground=[("disabled", c["text_faint"])],
    )
    style.configure(
        "Secondary.TButton", background=c["surface"], foreground=c["text"],
        font=fonts.body_soft, padding=(10, 7), relief="solid", borderwidth=1,
        bordercolor=c["divider"], lightcolor=c["divider"], darkcolor=c["divider"],
    )
    style.map(
        "Secondary.TButton",
        background=[("pressed", c["divider"]), ("active", c["neutral_200"])],
        bordercolor=[("active", c["accent"])],
        lightcolor=[("active", c["accent"])],
        darkcolor=[("active", c["accent"])],
    )
    style.configure(
        "Rail.TButton", background=c["bg"], foreground=c["text"],
        font=fonts.body_soft, padding=(10, 7), relief="flat", borderwidth=0,
        anchor="w",
    )
    style.map("Rail.TButton", background=[("active", c["surface"])])

    # ---- Checkbutton ----
    style.configure("TCheckbutton", background=c["bg"], foreground=c["text"], font=fonts.body_soft)
    style.map("TCheckbutton", background=[("active", c["bg"])])

    # ---- Segmented control: Toolbutton layout has no indicator dot ----
    style.configure(
        "Seg.Toolbutton", background=c["bg"], foreground=c["text"],
        font=fonts.body_soft, padding=(0, 6), relief="solid", anchor="center",
        borderwidth=1, bordercolor=c["divider"], lightcolor=c["divider"], darkcolor=c["divider"],
    )
    style.map(
        "Seg.Toolbutton",
        background=[("selected", c["accent"]), ("active", c["accent_100"])],
        foreground=[("selected", c["bg"])],
        bordercolor=[("selected", c["accent"])],
        lightcolor=[("selected", c["accent"])],
        darkcolor=[("selected", c["accent"])],
    )

    # ---- Combobox ----
    style.configure(
        "TCombobox", fieldbackground=c["surface"], foreground=c["text"],
        bordercolor=c["divider"], arrowsize=12, padding=4,
    )

    # ---- Notebook (used only if needed) ----
    style.configure("TNotebook", background=c["bg"], borderwidth=0)
    style.configure("TNotebook.Tab", background=c["bg"], font=fonts.section, padding=(10, 6))

    # ---- Scrollbar: keep native but flatten a bit ----
    style.configure("Vertical.TScrollbar", background=c["divider"], troughcolor=c["bg"], borderwidth=0, arrowsize=12)

    # ---- Treeview (frequency table) ----
    style.configure(
        "Treeview", background=c["bg"], fieldbackground=c["bg"], foreground=c["text"],
        font=fonts.mono, rowheight=22, borderwidth=0,
    )
    style.configure("Treeview.Heading", background=c["surface"], foreground=c["text_soft"], font=fonts.section)
    style.map("Treeview", background=[("selected", c["accent_100"])], foreground=[("selected", c["accent_900"])])

    return style, fonts
