"""Synthetic monitoring wells (labelled synthetic, not field data)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Well:
    head: np.ndarray        # monthly groundwater head (m above datum), shape (T,)
    rain: np.ndarray        # monthly rainfall index, shape (T,)
    pumping: np.ndarray     # monthly abstraction index, shape (T,)
    station: str = ""
    site_id: str = ""
    latitude: float = float("nan")
    longitude: float = float("nan")
    county: str = ""
    coord_ok: bool = True
    # Cumulative vertical displacement (m) on the same monthly index as head, if known.
    displacement: np.ndarray | None = None


def make_wells(n_wells: int, months: int, rng: np.random.Generator,
               pumping_growth: float = 1.0, break_month: int | None = None,
               break_factor: float = 1.0) -> list[Well]:
    """Head follows h[t+1] = h[t] + a*rain[t] - b*pumping[t] - c*(h[t]-h_eq) + noise.
    After `break_month`, abstraction is multiplied by `break_factor` (a regime change)."""
    wells = []
    t = np.arange(months)
    season = np.sin(2 * np.pi * t / 12)
    for _ in range(n_wells):
        a, b, c = rng.uniform(0.08, 0.14), rng.uniform(0.05, 0.12), rng.uniform(0.01, 0.03)
        h_eq = rng.uniform(40, 60)
        rain = np.clip(1.0 + 0.8 * season + rng.normal(0, 0.3, months), 0, None)
        base = rng.uniform(0.8, 1.6) * pumping_growth
        pump = base * (1.0 + 0.3 * np.sin(2 * np.pi * (t - 3) / 12)) * (1.0 + 0.002 * t)
        if break_month is not None:
            pump = np.where(t >= break_month, pump * break_factor, pump)
        h = np.empty(months)
        h[0] = h_eq
        for i in range(months - 1):
            h[i + 1] = (h[i] + a * rain[i] - b * pump[i] - c * (h[i] - h_eq)
                        + rng.normal(0, 0.05))
        wells.append(Well(h, rain, pump))
    return wells


def subsidence(head: np.ndarray, preconsolidation: float, compressibility: float = 0.01):
    """Cumulative subsidence (m): proportional to head decline below the preconsolidation head."""
    return compressibility * np.clip(preconsolidation - head, 0.0, None)
