# -*- coding: utf-8 -*-
"""Reusable pieces of the Industry-styled UI: blueprint corner marks,
labeled sections, spec tiles, the workflow step rail, the class segmented
control, validated fields and the stability badge.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from .theme import COLORS, Fonts, ramp_rgb


# ----------------------------------------------------------------------
# Blueprint chrome
# ----------------------------------------------------------------------

def add_corners(frame: tk.Widget, color: Optional[str] = None, size: int = 7) -> None:
    """Attach four small L-shaped registration marks to the corners of
    `frame`, echoing the mockup's `.corner` decoration on "blueprint" panels.
    """
    color = color or COLORS["text"]
    bg = frame["bg"] if "bg" in frame.keys() else COLORS["bg"]
    specs = {
        "nw": [(0, size, 0, 0), (0, 0, size, 0)],
        "ne": [(-size - 1, 0, 0, 0), (0, 0, 0, size)],
        "sw": [(0, 0, 0, size), (0, size, size, size)],
        "se": [(-size - 1, size, 0, size), (0, 0, 0, size)],
    }
    for anchor, lines in specs.items():
        cv = tk.Canvas(frame, width=size + 1, height=size + 1, highlightthickness=0, bg=bg, bd=0)
        for (x0, y0, x1, y1) in lines:
            x0 = x0 + size if x0 < 0 else x0
            x1 = x1 + size if x1 < 0 else x1
            cv.create_line(x0, y0, x1, y1, fill=color, width=1)
        relx = 0.0 if "w" in anchor else 1.0
        rely = 0.0 if "n" in anchor else 1.0
        cv.place(relx=relx, rely=rely, anchor={"nw": "nw", "ne": "ne", "sw": "sw", "se": "se"}[anchor])


class BlueprintFrame(tk.Frame):
    """A thin-bordered flat panel with blueprint corner marks."""

    def __init__(self, parent, bg=None, border=None, corners=True, **kw):
        bg = bg or COLORS["bg"]
        border = border or COLORS["divider"]
        super().__init__(parent, bg=bg, highlightthickness=1, highlightbackground=border, bd=0, **kw)
        if corners:
            add_corners(self, color=COLORS["text"])


# ----------------------------------------------------------------------
# Layout helpers
# ----------------------------------------------------------------------

class Section(ttk.Frame):
    """An uppercase micro-label followed by a content area, matching the
    mockup's `.sec` group headers ("FUENTE", "SUPUESTOS ACTIVOS", ...)."""

    def __init__(self, parent, title: str, fonts: Fonts, divider_above: bool = False, **kw):
        super().__init__(parent, **kw)
        self.columnconfigure(0, weight=1)
        row = 0
        if divider_above:
            sep = tk.Frame(self, height=1, bg=COLORS["divider"])
            sep.grid(row=row, column=0, sticky="ew", pady=(0, 10))
            row += 1
        if title:
            lbl = ttk.Label(self, text=title.upper(), style="Section.TLabel")
            lbl.grid(row=row, column=0, sticky="w", pady=(0, 8))
            row += 1
        self.body = ttk.Frame(self)
        self.body.grid(row=row, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)


class SpecTile(ttk.Frame):
    """A big-number readout: small caption, big value, small unit."""

    def __init__(self, parent, caption: str, unit: str, fonts: Fonts, big=False, **kw):
        super().__init__(parent, padding=(13, 11), **kw)
        ttk.Label(self, text=caption, style="Faint.TLabel").pack(anchor="w", pady=(0, 5))
        row = ttk.Frame(self)
        row.pack(anchor="w", fill="x")
        self.value_var = tk.StringVar(value="--")
        font = fonts.spec_n_lg if big else fonts.spec_n
        self.value_lbl = tk.Label(row, textvariable=self.value_var, font=font,
                                   bg=COLORS["bg"], fg=COLORS["accent_900"])
        self.value_lbl.pack(side="left")
        ttk.Label(row, text=" " + unit, style="Faint.TLabel").pack(side="left", anchor="s", pady=(0, 3))

    def set(self, text: str) -> None:
        self.value_var.set(text)


class RampLegend(tk.Frame):
    """Vertical low->high gradient legend bar for the concentration map."""

    def __init__(self, parent, width=18, height=140, **kw):
        super().__init__(parent, bg=COLORS["bg"], **kw)
        self.canvas = tk.Canvas(self, width=width, height=height, highlightthickness=1,
                                 highlightbackground=COLORS["divider"], bd=0)
        self.canvas.pack()
        img = tk.PhotoImage(width=width, height=height)
        for row in range(height):
            t = 1.0 - row / max(height - 1, 1)
            r, g, b = ramp_rgb(t)
            img.put(f"#{r:02x}{g:02x}{b:02x}", to=(0, row, width, row + 1))
        self._img = img  # keep a reference alive
        self.canvas.create_image(0, 0, anchor="nw", image=img)


# ----------------------------------------------------------------------
# Workflow step rail (vertical, main workbench)
# ----------------------------------------------------------------------

class VerticalStepRail(ttk.Frame):
    def __init__(self, parent, steps: list[tuple[str, str]], fonts: Fonts,
                 on_select: Callable[[str], None], **kw):
        super().__init__(parent, **kw)
        self._fonts = fonts
        self._on_select = on_select
        self._rows: dict[str, dict] = {}
        self._active = steps[0][0]
        for i, (step_id, label) in enumerate(steps, start=1):
            row = tk.Frame(self, bg=COLORS["bg"], cursor="hand2")
            row.pack(fill="x")
            bar = tk.Frame(row, width=2, bg=COLORS["bg"])
            bar.pack(side="left", fill="y")
            inner = tk.Frame(row, bg=COLORS["bg"])
            inner.pack(side="left", fill="x", expand=True, padx=(8, 14), pady=7)
            num = tk.Label(inner, text=str(i), font=fonts.heading, width=2,
                            bg=COLORS["bg"], fg=COLORS["text"],
                            highlightthickness=1, highlightbackground=COLORS["divider"])
            num.pack(side="left")
            lbl = tk.Label(inner, text=label, font=fonts.body, bg=COLORS["bg"], fg=COLORS["text"])
            lbl.pack(side="left", padx=(10, 0))
            for w in (row, bar, inner, num, lbl):
                w.bind("<Button-1>", lambda _e, sid=step_id: self._on_select(sid))
            self._rows[step_id] = {"row": row, "bar": bar, "num": num, "lbl": lbl}
        self.set_active(steps[0][0])

    def set_active(self, step_id: str) -> None:
        self._active = step_id
        for sid, w in self._rows.items():
            active = sid == step_id
            bg = COLORS["accent_100"] if active else COLORS["bg"]
            w["row"].configure(bg=bg)
            w["bar"].configure(bg=COLORS["accent"] if active else COLORS["bg"])
            for widget in w["row"].winfo_children():
                widget.configure(bg=bg)
            w["num"].configure(
                bg=COLORS["accent"] if active else bg,
                fg=COLORS["bg"] if active else COLORS["text"],
                highlightbackground=COLORS["accent"] if active else COLORS["divider"],
            )
            w["lbl"].configure(bg=bg, font=self._fonts.heading if active else self._fonts.body)


# ----------------------------------------------------------------------
# Horizontal step tracker (study mode breadcrumb)
# ----------------------------------------------------------------------

class HorizontalStepTracker(ttk.Frame):
    def __init__(self, parent, steps: list[str], fonts: Fonts, **kw):
        super().__init__(parent, padding=(20, 12), **kw)
        self._fonts = fonts
        self._nums: list[tk.Label] = []
        self._lbls: list[ttk.Label] = []
        for i, label in enumerate(steps):
            if i > 0:
                tk.Frame(self, width=26, height=1, bg=COLORS["divider"]).pack(side="left", padx=6)
            num = tk.Label(self, text=str(i + 1), font=fonts.body, width=2,
                            bg=COLORS["bg"], fg=COLORS["text"],
                            highlightthickness=1, highlightbackground=COLORS["divider"])
            num.pack(side="left")
            lbl = ttk.Label(self, text=label, style="Soft.TLabel")
            lbl.pack(side="left", padx=(8, 0))
            self._nums.append(num)
            self._lbls.append(lbl)
        self.set_active(0)

    def set_active(self, index: int) -> None:
        for i, (num, lbl) in enumerate(zip(self._nums, self._lbls)):
            if i < index:
                num.configure(text="✓", bg=COLORS["accent_700"], fg=COLORS["bg"],
                              highlightbackground=COLORS["accent_700"])
                lbl.configure(style="Soft.TLabel")
            elif i == index:
                num.configure(text=str(i + 1), bg=COLORS["accent"], fg=COLORS["bg"],
                              highlightbackground=COLORS["accent"])
                lbl.configure(style="Heading.TLabel")
            else:
                num.configure(text=str(i + 1), bg=COLORS["bg"], fg=COLORS["text"],
                              highlightbackground=COLORS["divider"])
                lbl.configure(style="Soft.TLabel")


# ----------------------------------------------------------------------
# Stability badge ("Estabilidad activa")
# ----------------------------------------------------------------------

STABILITY_DESC = {
    "A": "Muy inestable", "B": "Inestable", "C": "Ligeramente inestable",
    "D": "Neutra", "E": "Estable", "F": "Muy estable",
}


class StabilityBadge(ttk.Frame):
    def __init__(self, parent, fonts: Fonts, **kw):
        super().__init__(parent, **kw)
        row = ttk.Frame(self)
        row.pack(anchor="w", fill="x")
        self.letter_var = tk.StringVar(value="D")
        tk.Label(row, textvariable=self.letter_var, font=fonts.badge,
                 bg=COLORS["bg"], fg=COLORS["accent_800"]).pack(side="left")
        self.desc_var = tk.StringVar(value="Neutra")
        desc = ttk.Label(row, textvariable=self.desc_var, style="Soft.TLabel", justify="left")
        desc.pack(side="left", padx=(8, 0), anchor="n", pady=(4, 0))
        self.source_var = tk.StringVar(value="fija por el usuario")
        ttk.Label(self, textvariable=self.source_var, style="Faint.TLabel").pack(anchor="w", pady=(2, 8))

        info = ttk.Frame(self)
        info.pack(fill="x")
        info.columnconfigure(1, weight=1)
        self.p_var = tk.StringVar(value="0.25")
        ttk.Label(info, text="p (ley exp.)", style="Faint.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(info, textvariable=self.p_var, style="Faint.TLabel").grid(row=0, column=1, sticky="e")
        ttk.Label(info, text="σy, σz", style="Faint.TLabel").grid(row=1, column=0, sticky="w")
        ttk.Label(info, text="P-G rural", style="Faint.TLabel").grid(row=1, column=1, sticky="e")

    def set_class(self, clase: str, p: float) -> None:
        self.letter_var.set(clase)
        self.desc_var.set(STABILITY_DESC.get(clase, "Neutra"))
        self.p_var.set(f"{p:.2f}")


# ----------------------------------------------------------------------
# Class segmented control (A..F)
# ----------------------------------------------------------------------

class ClassSegmented(ttk.Frame):
    def __init__(self, parent, variable: tk.StringVar, command: Callable[[], None], **kw):
        super().__init__(parent, **kw)
        for i, c in enumerate("ABCDEF"):
            self.columnconfigure(i, weight=1)
            b = ttk.Radiobutton(self, text=c, value=c, variable=variable, style="Seg.Toolbutton",
                                 command=command)
            b.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 1, 0))


class ErrorBanner(ttk.Frame):
    """Full-width message that names the field it accuses, for validation
    text too long to sit inside a half-width cell."""

    def __init__(self, parent, tag: str, fonts: Fonts, wrap: int = 250, **kw):
        super().__init__(parent, **kw)
        self._box = tk.Frame(self, bg=COLORS["error_bg"])
        tk.Frame(self._box, width=2, bg=COLORS["error_border"]).pack(side="left", fill="y")
        inner = tk.Frame(self._box, bg=COLORS["error_bg"])
        inner.pack(side="left", fill="both", expand=True, padx=10, pady=8)
        tk.Label(inner, text=tag, font=fonts.section, bg=COLORS["error_bg"],
                 fg=COLORS["error_text"]).pack(side="left", anchor="n", padx=(0, 8))
        self._var = tk.StringVar()
        tk.Label(inner, textvariable=self._var, font=fonts.body_soft, bg=COLORS["error_bg"],
                 fg=COLORS["error_text_soft"], wraplength=wrap, justify="left").pack(side="left", anchor="w")

    def show(self, message: str) -> None:
        self._var.set(message)
        if not self._box.winfo_ismapped():
            self._box.pack(fill="x")

    def hide(self) -> None:
        self._box.pack_forget()


# ----------------------------------------------------------------------
# Validated numeric field
# ----------------------------------------------------------------------

class ValidatedField(ttk.Frame):
    """Label + entry + inline validation message.

    A `rule(value: float) -> (ok, message)` decides validity (message is
    only shown when not ok). Invalid input keeps the entry's *last valid*
    value available via `.value`, matching the mockup's rule that the
    map/results keep showing the last valid case while the offending
    field is flagged in place.
    """

    def __init__(self, parent, label: str, unit: str, default: float, fonts: Fonts,
                 rule: Optional[Callable[[float], tuple[bool, str]]] = None,
                 on_commit: Optional[Callable[[], None]] = None,
                 hint: Optional[str] = None, width=None, wrap: int = 240,
                 error_host: Optional["ErrorBanner"] = None, **kw):
        super().__init__(parent, **kw)
        self._rule = rule or (lambda v: (True, ""))
        self._on_commit = on_commit
        self._value = float(default)
        self._valid = True
        self._touched = False

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text=label, style="Soft.TLabel").pack(side="left")
        if unit:
            ttk.Label(top, text=" " + unit, style="Faint.TLabel").pack(side="left")

        self.var = tk.StringVar(value=f"{default:g}")
        entry_kw = {"width": width} if width is not None else {}
        self.entry = ttk.Entry(self, textvariable=self.var, font=fonts.body, **entry_kw)
        self.entry.pack(fill="x", pady=(4, 0))

        self.hint_var = tk.StringVar(value=hint or "")
        self.hint_lbl = ttk.Label(self, textvariable=self.hint_var, style="Faint.TLabel",
                                   wraplength=wrap, justify="left")
        if hint:
            self.hint_lbl.pack(anchor="w", pady=(3, 0))

        self._error_host = error_host
        self.error_var = tk.StringVar(value="")
        if error_host is None:
            self.error_lbl = ttk.Label(self, textvariable=self.error_var, style="Error.TLabel",
                                        wraplength=wrap, justify="left")

        self.entry.bind("<KeyRelease>", self._on_key)
        self.entry.bind("<FocusOut>", self._on_key)
        self.entry.bind("<Return>", self._on_return)

    @property
    def value(self) -> float:
        return self._value

    def set_enabled(self, enabled: bool) -> None:
        self.entry.state(["!disabled" if enabled else "disabled"])

    def _validate_current(self) -> bool:
        text = self.var.get().strip()
        try:
            v = float(text)
            ok, msg = self._rule(v)
        except ValueError:
            ok, msg = False, "Debe ser un número."
        if ok:
            self._value = v
            self._valid = True
            # Accent border only once the user has touched the field, so a
            # corrected value reads as confirmed instead of merely neutral.
            self.entry.configure(style="Valid.TEntry" if self._touched else "TEntry")
            self.error_var.set("")
            if self._error_host is not None:
                self._error_host.hide()
            else:
                self.error_lbl.pack_forget()
        else:
            self._valid = False
            self.entry.configure(style="Error.TEntry")
            self.error_var.set(msg)
            if self._error_host is not None:
                self._error_host.show(msg)
            elif not self.error_lbl.winfo_ismapped():
                self.error_lbl.pack(anchor="w", pady=(3, 0), fill="x")
        return ok

    def _on_key(self, _event=None):
        self._touched = True
        self._validate_current()

    def _on_return(self, _event=None):
        self._validate_current()
        if self._on_commit:
            self._on_commit()
