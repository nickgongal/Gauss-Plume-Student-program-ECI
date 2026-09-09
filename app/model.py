# -*- coding: utf-8 -*-
"""Grid/curve computation shared by every view (workbench, full-bleed map,
study mode). Mirrors the original app's `_run_calculation`, but returns
data instead of drawing it, so different layouts can render it differently.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import physics
from .physics import Params


@dataclass
class Result:
    params: Params
    iso_val: float
    x: np.ndarray            # (nx,) longitudinal axis
    y: np.ndarray            # (nx,) transversal axis
    X: np.ndarray            # meshgrid
    Y: np.ndarray
    Z: np.ndarray             # concentration field, ug/m3
    line: np.ndarray          # centerline curve C(x, y=0), ug/m3
    u_eff: float
    H_final: float
    F: float
    p: float
    cmax: float
    xmax: float
    area_m2: float


def compute(params: Params, iso_val: float, nx: int | None = None) -> Result:
    nx = int(nx or np.clip(params.max_dist / 10.0, 150, 400))
    x = np.linspace(0.0, params.max_dist, nx)
    y = np.linspace(-params.trans_width / 2.0, params.trans_width / 2.0, nx)
    X, Y = np.meshgrid(x, y)

    state = physics.solve_profile(params, X)
    Z = physics.concentration(params, state, X, Y, params.z_rec)

    finite = np.isfinite(Z)
    cmax, xmax = 0.0, 0.0
    if np.any(finite):
        idx_flat = np.argmax(Z[finite])
        pos = np.flatnonzero(finite)[idx_flat]
        iy, ix = np.unravel_index(pos, Z.shape)
        approx_x = X[iy, ix]

        search_range = 200.0
        x_min_f = max(1.0, float(approx_x) - search_range)
        x_max_f = min(float(params.max_dist), float(approx_x) + search_range)
        x_fine = np.linspace(x_min_f, x_max_f, 1000)
        y_fine = np.zeros_like(x_fine)

        state_fine = physics.solve_profile(params, x_fine)
        C_fine = physics.concentration(params, state_fine, x_fine, y_fine, params.z_rec)

        idx_fine = int(np.argmax(C_fine))
        cmax = float(C_fine[idx_fine])
        xmax = float(x_fine[idx_fine])

    area_m2 = 0.0
    if iso_val > 0.0 and np.any(finite) and len(x) > 1 and len(y) > 1:
        dx = x[1] - x[0]
        dy = y[1] - y[0]
        area_m2 = float(np.sum(Z >= iso_val) * dx * dy)

    mid = int(np.argmin(np.abs(y)))
    line = Z[mid]

    return Result(
        params=params, iso_val=iso_val,
        x=x, y=y, X=X, Y=Y, Z=Z, line=line,
        u_eff=state.u_eff, H_final=state.H_final, F=state.F, p=state.p,
        cmax=cmax, xmax=xmax, area_m2=area_m2,
    )


def format_area(value: float) -> str:
    """Thousands separated the Spanish way: 37.500 m²."""
    return f"{value:,.0f}".replace(",", ".")


def point_result(params: Params, x: float, y: float, z: float) -> dict:
    C, state, sigma_y, sigma_z = physics.concentration_at(params, x, y, z)
    return {
        "c": C,
        "u_eff": state.u_eff,
        "h": float(state.H_field[0]),
        "sigma_y": sigma_y,
        "sigma_z": sigma_z,
    }
