# -*- coding: utf-8 -*-
"""Entry point and application state for the modernized plume-dispersion
workbench. Ties together the physics/model layer with the workbench,
full-bleed map, study-mode and point-calculation views.
"""

from __future__ import annotations

import csv
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import numpy as np

from . import model, physics
from .model import format_area
from .theme import COLORS, apply_theme

DEFAULTS = dict(
    q=10.0, h=50.0, u=5.0, z_rec=0.0, max_dist=5000.0, trans_width=1000.0,
    d=2.0, vs=15.0, Ts=420.0, Ta=300.0,
)


class PlumeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Modelo Gaussiano de Pluma — v4.0 · Briggs + Pasquill-Gifford")
        self.geometry("1600x1000")
        self.minsize(1280, 860)
        try:
            self.state("zoomed")
        except tk.TclError:
            pass

        self.style, self.fonts = apply_theme(self)

        # ---- canonical model state ----
        self.p = physics.Params(clase="A", **DEFAULTS)
        self.iso_val = 25.0
        self.dominant_enabled = False
        self.freqs_serie: dict | None = None
        self.clases_serie: np.ndarray | None = None
        self.result: model.Result | None = None
        self.last_point: dict | None = None

        self.use_auto_H_var = tk.BooleanVar(value=self.p.use_auto_H)
        self.use_wind_var = tk.BooleanVar(value=self.p.use_wind_correction)
        self.view_mode_var = tk.StringVar(value="workbench")

        self._build_menu()
        self._build_status_bar()

        self.view_container = ttk.Frame(self)
        self.view_container.pack(fill="both", expand=True)
        self.view = None
        self._build_view("workbench")
        self.recompute()

    # ------------------------------------------------------------------
    # Chrome: menu + status bar
    # ------------------------------------------------------------------

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)

        m_archivo = tk.Menu(menubar, tearoff=0)
        m_archivo.add_command(label="Nuevo caso", command=self.reset_case)
        m_archivo.add_separator()
        m_archivo.add_command(label="Salir", command=self.destroy)
        menubar.add_cascade(label="Archivo", menu=m_archivo)

        m_modelo = tk.Menu(menubar, tearoff=0)
        m_modelo.add_checkbutton(label="Elevación de pluma (Briggs)", variable=self.use_auto_H_var,
                                  command=self._on_briggs_toggle)
        m_modelo.add_checkbutton(label="Corregir viento (ley exponencial)", variable=self.use_wind_var,
                                  command=self._on_wind_toggle)
        menubar.add_cascade(label="Modelo", menu=m_modelo)

        m_serie = tk.Menu(menubar, tearoff=0)
        m_serie.add_command(label="Generar serie demo de 24 h", command=self.generate_demo_series)
        m_serie.add_command(label="Aplicar frecuencias manuales", command=self.apply_manual_freqs)
        menubar.add_cascade(label="Serie", menu=m_serie)

        m_ver = tk.Menu(menubar, tearoff=0)
        m_ver.add_radiobutton(label="Banco de trabajo", variable=self.view_mode_var, value="workbench",
                               command=lambda: self._build_view("workbench"))
        m_ver.add_radiobutton(label="Mapa a sangre", variable=self.view_mode_var, value="fullbleed",
                               command=lambda: self._build_view("fullbleed"))
        m_ver.add_separator()
        m_ver.add_command(label="Modo estudio…", command=self.open_study_mode)
        menubar.add_cascade(label="Ver", menu=m_ver)

        m_ayuda = tk.Menu(menubar, tearoff=0)
        m_ayuda.add_command(label="Información / Ayuda", command=self.show_info)
        menubar.add_cascade(label="Ayuda", menu=m_ayuda)

        self.configure(menu=menubar)

    def _build_status_bar(self) -> None:
        bar = ttk.Frame(self, padding=(12, 5))
        bar.pack(fill="x")
        sep = tk.Frame(self, height=1, bg=COLORS["divider"])
        sep.pack(fill="x")
        self.status_dot = tk.Label(bar, text="●", fg=COLORS["accent"], bg=COLORS["bg"])
        self.status_dot.pack(side="right", padx=(6, 0))
        self.status_var = tk.StringVar(value="Cálculo al día")
        ttk.Label(bar, textvariable=self.status_var, style="Accent.TLabel").pack(side="right")

    # ------------------------------------------------------------------
    # View switching
    # ------------------------------------------------------------------

    def _build_view(self, mode: str) -> None:
        for child in self.view_container.winfo_children():
            child.destroy()
        self.view_mode_var.set(mode)
        if mode == "workbench":
            from .workbench import WorkbenchView
            self.view = WorkbenchView(self.view_container, self)
        else:
            from .fullbleed_view import FullBleedView
            self.view = FullBleedView(self.view_container, self)
        if self.result is not None:
            self.view.refresh()

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------

    def selected_class(self) -> str:
        if self.dominant_enabled:
            if self.freqs_serie:
                return max(self.freqs_serie, key=self.freqs_serie.get)
            return "D"
        return self.p.clase

    def recompute(self) -> None:
        self.p.clase = self.selected_class()
        self.p.use_auto_H = self.use_auto_H_var.get()
        self.p.use_wind_correction = self.use_wind_var.get()
        self.configure(cursor="watch")
        self.update_idletasks()
        try:
            self.result = model.compute(self.p, self.iso_val)
        finally:
            self.configure(cursor="")
        self.status_var.set("Cálculo al día")
        if self.view is not None:
            self.view.refresh()

    def _on_briggs_toggle(self) -> None:
        self.p.use_auto_H = self.use_auto_H_var.get()
        if hasattr(self.view, "_on_briggs_toggle"):
            self.view._on_briggs_toggle()
        else:
            self.recompute()

    def _on_wind_toggle(self) -> None:
        self.p.use_wind_correction = self.use_wind_var.get()
        self.recompute()

    def reset_case(self) -> None:
        self.p = physics.Params(clase="A", **DEFAULTS)
        self.iso_val = 25.0
        self.dominant_enabled = False
        self.freqs_serie = None
        self.clases_serie = None
        self.last_point = None
        self.use_auto_H_var.set(True)
        self.use_wind_var.set(True)
        self._build_view(self.view_mode_var.get())
        self.recompute()

    # ------------------------------------------------------------------
    # Point calculation
    # ------------------------------------------------------------------

    def calc_point(self, x: float, y: float, z: float) -> dict:
        r = model.point_result(self.p, x, y, z)
        self.last_point = {"x": x, "y": y, "z": z, **r}
        if hasattr(self.view, "show_point_result"):
            self.view.show_point_result(x, y, z, r)
        self.recompute()
        return r

    def open_point_dialog(self) -> None:
        from .point_dialog import PointDialog
        PointDialog(self)

    # ------------------------------------------------------------------
    # Frequencies
    # ------------------------------------------------------------------

    def apply_manual_freqs(self) -> None:
        view = self.view
        if not hasattr(view, "freq_fields"):
            messagebox.showinfo("Frecuencias manuales",
                                 "Cambia a la vista Banco de trabajo (paso Meteorología) para editar frecuencias manuales.")
            return
        try:
            raw = {c: float(view.freq_fields[c].get()) for c in "ABCDEF"}
            if any(v < 0 for v in raw.values()):
                raise ValueError("Las frecuencias no pueden ser negativas.")
            s = sum(raw.values())
            if s <= 0:
                raise ValueError("La suma de frecuencias debe ser mayor que 0.")
            freqs = {k: v / s for k, v in raw.items()}
        except ValueError as e:
            messagebox.showerror("Error en frecuencias", str(e))
            return
        self.freqs_serie = freqs
        self.clases_serie = None
        self.recompute()
        messagebox.showinfo("Frecuencias aplicadas",
                             "Frecuencias manuales aplicadas y normalizadas.\n"
                             "'Usar clase dominante' tomará la clase con mayor frecuencia.")

    def generate_demo_series(self) -> None:
        N = 24
        horas = np.arange(N)
        es_dia = np.array([(8 <= h <= 17) for h in horas])
        v = np.linspace(1.5, 6.5, N)
        G = []
        for i, d in enumerate(es_dia):
            if d and 10 <= horas[i] <= 14:
                G.append(800.0)
            elif d:
                G.append(400.0)
            else:
                G.append(None)
        n_ok = [None if d else 2 for d in es_dia]

        self.clases_serie = physics.StabilityModule.series_pg(es_dia, v, G, n_ok)
        self.freqs_serie = physics.StabilityModule.frecuencias(self.clases_serie)
        self.recompute()
        messagebox.showinfo("Serie generada",
                             "Serie demo de 24 h generada correctamente.\n"
                             "'Usar clase dominante' tomará la clase más frecuente.")

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_csv(self) -> None:
        if self.result is None:
            messagebox.showwarning("Sin datos", "Primero ejecute el modelo para generar la curva.")
            return
        fpath = filedialog.asksaveasfilename(defaultextension=".csv",
                                              filetypes=[("CSV", "*.csv"), ("Todos los archivos", "*.*")])
        if not fpath:
            return
        try:
            with open(fpath, "w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh, delimiter=";")
                writer.writerow(["Distancia_x_m", "Concentracion_y0_ugm3"])
                for xv, cv in zip(self.result.x, self.result.line):
                    writer.writerow([f"{xv:.2f}", f"{cv:.6f}"])
            messagebox.showinfo("Exportado", "Curva exportada correctamente.")
        except OSError as e:
            messagebox.showerror("Error al exportar", str(e))

    def save_png(self) -> None:
        if self.view is None or not hasattr(self.view, "fig"):
            messagebox.showwarning("Sin gráfica", "Esta vista no tiene una figura exportable.")
            return
        fpath = filedialog.asksaveasfilename(defaultextension=".png",
                                              filetypes=[("PNG", "*.png"), ("Todos los archivos", "*.*")])
        if not fpath:
            return
        try:
            self.view.fig.savefig(fpath, dpi=300, facecolor=COLORS["bg"])
            messagebox.showinfo("Guardado", "Gráfica guardada en alta resolución (300 dpi).")
        except OSError as e:
            messagebox.showerror("Error al guardar", str(e))

    def export_report(self) -> None:
        if self.result is None:
            messagebox.showwarning("Sin datos", "Primero ejecute el modelo.")
            return
        fpath = filedialog.asksaveasfilename(defaultextension=".txt",
                                              filetypes=[("Texto", "*.txt"), ("Todos los archivos", "*.*")])
        if not fpath:
            return
        r, p = self.result, self.p
        lines = [
            "INFORME DEL CASO — Modelo Gaussiano de Pluma v4.0",
            "=" * 52,
            f"Clase de estabilidad: {p.clase}  (p = {r.p:.2f})",
            "",
            "Parametros de la fuente:",
            f"  Q  (emision)        : {p.q:g} g/s",
            f"  Hs (chimenea)       : {p.h:g} m",
            f"  d  (diametro)       : {p.d:g} m",
            f"  vs (salida)         : {p.vs:g} m/s",
            f"  Ts (gases)          : {p.Ts:g} K",
            f"  Ta (ambiente)       : {p.Ta:g} K",
            f"  u10 (viento)        : {p.u:g} m/s",
            "",
            "Dominio y receptor:",
            f"  X max               : {p.max_dist:g} m",
            f"  Ancho Y             : {p.trans_width:g} m",
            f"  z receptor          : {p.z_rec:g} m",
            "",
            "Resultados:",
            f"  u_eff               : {r.u_eff:.2f} m/s",
            f"  H_eff               : {r.H_final:.1f} m",
            f"  C max               : {r.cmax:.2f} ug/m3",
            f"  x en C max          : {r.xmax:.1f} m",
            f"  Limite isopleta     : {self.iso_val:g} ug/m3",
            f"  Area con C >= limite: {format_area(r.area_m2)} m2",
        ]
        try:
            with open(fpath, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + "\n")
            messagebox.showinfo("Informe exportado", "Informe del caso guardado correctamente.")
        except OSError as e:
            messagebox.showerror("Error al exportar", str(e))

    # ------------------------------------------------------------------
    # Secondary windows
    # ------------------------------------------------------------------

    def open_study_mode(self) -> None:
        from .study_mode import StudyWindow
        StudyWindow(self)

    def show_info(self) -> None:
        from .info_window import show_info_window
        show_info_window(self)


def main() -> None:
    app = PlumeApp()
    app.mainloop()


if __name__ == "__main__":
    main()
