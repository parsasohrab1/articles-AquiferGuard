"""Ridge forecast of head h months ahead with split-conformal intervals."""

from __future__ import annotations

import numpy as np

from .synth import Well

LAGS = 6


def features(w: Well, t: int) -> np.ndarray:
    """Predictors available at month t: recent heads, rain, abstraction, season."""
    h = w.head[t - LAGS + 1:t + 1]
    r = w.rain[t - LAGS + 1:t + 1]
    p = w.pumping[t - LAGS + 1:t + 1]
    s = [np.sin(2 * np.pi * t / 12), np.cos(2 * np.pi * t / 12)]
    return np.concatenate([h - h[-1], r, p, s, [h[-1]]])


def dataset(wells: list[Well], horizon: int, t0: int, t1: int):
    X, y, base = [], [], []
    for w in wells:
        for t in range(max(t0, LAGS), min(t1, len(w.head) - horizon)):
            X.append(features(w, t))
            y.append(w.head[t + horizon] - w.head[t])
            base.append(w.head[t])
    return np.array(X), np.array(y), np.array(base)


class Forecaster:
    def __init__(self, horizon: int = 6, ridge: float = 1.0):
        self.horizon, self.ridge = horizon, ridge

    def fit(self, wells, t0, t1):
        X, y, _ = dataset(wells, self.horizon, t0, t1)
        self.mean, self.std = X.mean(0), X.std(0) + 1e-9
        Z = np.c_[(X - self.mean) / self.std, np.ones(len(X))]
        reg = self.ridge * np.eye(Z.shape[1])
        reg[-1, -1] = 0
        self.w = np.linalg.solve(Z.T @ Z + reg, Z.T @ y)
        return self

    def predict_change(self, X):
        return np.c_[(X - self.mean) / self.std, np.ones(len(X))] @ self.w


def conformal_halfwidth(fc: Forecaster, wells, t0, t1, alpha: float = 0.1) -> float:
    X, y, _ = dataset(wells, fc.horizon, t0, t1)
    r = np.sort(np.abs(y - fc.predict_change(X)))
    k = int(np.ceil((len(r) + 1) * (1 - alpha)))
    return float(r[min(k, len(r)) - 1])


def coverage_and_error(fc: Forecaster, wells, t0, t1, half: float):
    X, y, _ = dataset(wells, fc.horizon, t0, t1)
    e = np.abs(y - fc.predict_change(X))
    return float(np.mean(e <= half)), float(e.mean())
