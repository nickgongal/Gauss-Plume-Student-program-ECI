# -*- coding: utf-8 -*-
"""Matplotlib figures styled like the mockup's canvas maps: the same
green->yellow->orange->red ramp (replacing the original's 'jet'), dark
dashed isopleth contours, and a centerline profile with a soft fill and
a marked maximum.
"""

from __future__ import annotations

import matplotlib
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure

from .theme import COLORS, RAMP_STOPS, ramp_rgb
from .model import Result

matplotlib.rcParams["font.family"] = "sans-serif"

PLUME_CMAP = LinearSegmentedColormap.from_list(
    "plume_ramp", [(t, (r / 255, g / 255, b / 255)) for t, (r, g, b) in RAMP_STOPS], N=256,
)


def _style_axes(ax, xlabel: str, ylabel: str) -> None:
    ax.set_facecolor(COLORS["bg"])
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(COLORS["divider"])
    ax.tick_params(colors=COLORS["text_soft"], labelsize=8, length=3)
    ax.set_xlabel(xlabel, fontsize=8.5, color=COLORS["text_soft"])
    ax.set_ylabel(ylabel, fontsize=8.5, color=COLORS["text_soft"])
    ax.grid(alpha=0.18, color=COLORS["text"], linewidth=0.6)


def new_figure(figsize=(8, 5), dpi=100) -> Figure:
    fig = Figure(figsize=figsize, dpi=dpi)
    fig.patch.set_facecolor(COLORS["bg"])
    return fig


def draw_contour(ax, result: Result, point=None) -> None:
    ax.clear()
    X, Y, Z = result.X, result.Y, result.Z
    vmax = max(float(np.nanmax(Z)), 1e-9)
    ax.contourf(X, Y, Z, levels=60, cmap=PLUME_CMAP, vmin=0, vmax=vmax)

    iso = result.iso_val
    if 0.0 < iso < vmax:
        ax.contour(X, Y, Z, levels=[iso], colors=[COLORS["text"]], linewidths=1.3,
                         linestyles="dashed", alpha=0.85)

    # stack marker at the source
    ax.plot([0], [0], marker="s", markersize=6, markerfacecolor=COLORS["bg"],
            markeredgecolor=COLORS["accent_900"], markeredgewidth=1.2, zorder=5)

    if point is not None:
        px, py = point
        ax.plot([px], [py], marker="+", markersize=11, markeredgewidth=1.8,
                color=COLORS["accent_900"], zorder=6)

    ax.set_xlim(result.x.min(), result.x.max())
    ax.set_ylim(result.y.min(), result.y.max())
    _style_axes(ax, "Distancia longitudinal x (m)", "Distancia transversal y (m)")


def draw_line(ax, result: Result) -> None:
    ax.clear()
    x, line = result.x, result.line
    top = max(result.cmax * 1.12, 1e-9)

    mid_t = min(result.cmax, top) / top if top else 0
    r, g, b = ramp_rgb(min(0.55, mid_t))
    fill_color = (r / 255, g / 255, b / 255)

    ax.fill_between(x, 0, line, color=fill_color, alpha=0.28, linewidth=0)
    ax.plot(x, line, color=COLORS["accent_900"], linewidth=1.6)

    if result.iso_val > 0:
        ax.axhline(result.iso_val, color=COLORS["accent_700"], linewidth=1, linestyle=(0, (5, 4)), alpha=0.7)

    if result.cmax > 0:
        ax.plot([result.xmax], [result.cmax], marker="x", markersize=8,
                 markeredgewidth=1.6, color=COLORS["accent_900"])
        ax.axvline(result.xmax, color=COLORS["accent_900"], linewidth=1, linestyle=(0, (3, 3)), alpha=0.35,
                   ymax=0.92)

    ax.set_xlim(0, result.x.max())
    ax.set_ylim(0, top)
    _style_axes(ax, "Distancia x (m)", "C (μg/m³)")
