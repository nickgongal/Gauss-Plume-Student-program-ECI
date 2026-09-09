# -*- coding: utf-8 -*-
"""Physics: Pasquill-Gifford stability, Briggs plume rise, wind power-law
correction and the Gaussian plume equation. Ported unchanged from the
original v4.0 Tkinter application (4dfd2412-4.0_11.02.26.py) so results
match exactly; only reorganized into plain functions/dataclasses and a
single `solve()` entry point that removes the two call sites that used
to duplicate the u_eff/H two-step iteration.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# ============================
# 0) PARAMETROS DE VIENTO (LEY EXPONENCIAL)
# ============================

WIND_EXPONENT_P = {
    "A": 0.15,
    "B": 0.15,
    "C": 0.20,
    "D": 0.25,
    "E": 0.40,
    "F": 0.60,
}


def viento_corregido_exponencial(u10_ms: float, z_m: float, clase_estabilidad: str) -> float:
    clase = (clase_estabilidad or "D").upper()
    p = float(WIND_EXPONENT_P.get(clase, 0.25))
    z_use = max(float(z_m), 1.0)
    u = float(u10_ms) * (z_use / 10.0) ** p
    return max(u, 0.10)


# ============================
# 1) MODULO DE ESTABILIDADES
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
        return np.array(clases, dtype="<U1")

    @staticmethod
    def frecuencias(clases: np.ndarray) -> dict[str, float]:
        counts = {c: float(np.sum(clases == c)) for c in "ABCDEF"}
        total = sum(counts.values()) or 1.0
        return {k: v / total for k, v in counts.items()}


# ============================
# 2) MODULO DE DISPERSION
# ============================

class DispersionModule:
    @staticmethod
    def sigmas(x: np.ndarray, clase_estabilidad: str):
        x = np.asarray(x, dtype=float)
        x = np.maximum(x, 0.001)

        clase = (clase_estabilidad or "D").upper()
        map_cls = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6}
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
# 3) MODULO DE PLUMA
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
                                    wind_speed_ms, x_array_m, clase_estabilidad="D"):
    x = np.asarray(x_array_m, dtype=float)
    g = 9.81

    delta_T = max(float(stack_temperature_K) - float(ambient_temperature_K), 0.0)
    Ts = max(float(stack_temperature_K), 1.0)
    F = g * float(exit_velocity_ms) * (float(stack_diameter_m) ** 2) * delta_T / (4.0 * Ts)

    if (float(stack_diameter_m) <= 0.0 or float(exit_velocity_ms) <= 0.0
            or float(wind_speed_ms) <= 0.0 or F < 1e-3):
        H_field = np.full_like(x, float(stack_height_m), dtype=float)
        return H_field, float(stack_height_m), F

    clase = (clase_estabilidad or "D").upper()
    u = float(wind_speed_ms)
    Hs = float(stack_height_m)
    Ta = max(float(ambient_temperature_K), 1.0)

    if clase in ["A", "B", "C", "D"]:
        if F < 55.0:
            x_f = 49.0 * (F ** 0.625)
        else:
            x_f = 119.0 * (F ** 0.4)

        delta_h_max = 1.6 * (F ** (1.0 / 3.0)) * (x_f ** (2.0 / 3.0)) / u
        delta_h_x = 1.6 * (F ** (1.0 / 3.0)) * (np.maximum(x, 0.0) ** (2.0 / 3.0)) / u
        delta_h_x = np.minimum(delta_h_x, delta_h_max)

        H_field = Hs + delta_h_x
        H_final = Hs + delta_h_max
        return H_field, float(H_final), F

    if clase == "E":
        dtheta_dz = 0.020
    else:
        dtheta_dz = 0.035

    s = max((g / Ta) * dtheta_dz, 1e-4)
    delta_h_max = 2.4 * (F / (u * s)) ** (1.0 / 3.0)
    delta_h_tmp = 1.6 * (F ** (1.0 / 3.0)) * (np.maximum(x, 0.0) ** (2.0 / 3.0)) / u
    delta_h_x = np.minimum(delta_h_tmp, delta_h_max)

    H_field = Hs + delta_h_x
    H_final = Hs + delta_h_max
    return H_field, float(H_final), F


# ============================
# 4) PARAMETROS Y ESTADO RESUELTO
# ============================

@dataclass
class Params:
    q: float
    h: float
    u: float
    z_rec: float
    max_dist: float
    trans_width: float
    d: float
    vs: float
    Ts: float
    Ta: float
    clase: str
    use_auto_H: bool = True
    use_wind_correction: bool = True


@dataclass
class SolvedState:
    """Everything derived from a Params + an array of x positions.

    Replaces the "estimate H_ref with u10, then recompute u_eff and H(x)"
    two-step scheme that appeared three times (main calc, refined-max
    search, point popup) in the original file.
    """

    x: np.ndarray
    H_field: np.ndarray
    H_final: float
    u_eff: float
    F: float
    p: float


def solve_profile(params: Params, x: np.ndarray) -> SolvedState:
    """Two-stage solve of u_eff and H(x) for the given x array."""
    p = float(WIND_EXPONENT_P.get((params.clase or "D").upper(), 0.25))
    u_in = float(params.u)

    if params.use_wind_correction:
        if params.use_auto_H:
            _, H_final_1, _ = altura_efectiva_briggs_profile(
                params.h, params.d, params.vs, params.Ts, params.Ta, u_in, x, params.clase
            )
            H_ref = float(H_final_1)
        else:
            H_ref = float(params.h)
        u_eff = viento_corregido_exponencial(u_in, H_ref, params.clase)
    else:
        u_eff = u_in

    if params.use_auto_H:
        H_field, H_final, F = altura_efectiva_briggs_profile(
            params.h, params.d, params.vs, params.Ts, params.Ta, u_eff, x, params.clase
        )
    else:
        H_final = float(params.h)
        H_field = np.full_like(np.asarray(x, dtype=float), H_final)
        _, _, F = altura_efectiva_briggs_profile(
            params.h, params.d, params.vs, params.Ts, params.Ta, u_eff, x, params.clase
        )

    return SolvedState(x=np.asarray(x, dtype=float), H_field=H_field, H_final=H_final, u_eff=u_eff, F=F, p=p)


def concentration(params: Params, state: SolvedState, x, y, z) -> np.ndarray:
    sigma_y, sigma_z = DispersionModule.sigmas(x, params.clase)
    C = PlumeModule.concentracion_gaussiana(
        params.q, state.H_field, state.u_eff, x, y, z, sigma_y, sigma_z
    )
    return C * 1e6  # g/m3 -> ug/m3


def concentration_at(params: Params, x: float, y: float, z: float) -> tuple[float, SolvedState, float, float]:
    """Point calculation: returns (C ug/m3, state, sigma_y, sigma_z) at a single x."""
    xa = np.array([float(x)])
    state = solve_profile(params, xa)
    sigma_y, sigma_z = DispersionModule.sigmas(xa, params.clase)
    C = concentration(params, state, xa, np.array([float(y)]), float(z))
    return float(C[0]), state, float(sigma_y[0]), float(sigma_z[0])
