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
    season = [np.sin(2 * np.pi * t / 12), np.cos(2 * np.pi * t / 12)]
    return np.concatenate([h - h[-1], r, p, season, [h[-1]]])


def head_features(w: Well, t: int) -> np.ndarray:
    """Past heads and season only. Rainfall and pumping are not used."""
    h = w.head[t - LAGS + 1:t + 1]
    season = [np.sin(2 * np.pi * t / 12), np.cos(2 * np.pi * t / 12)]
    return np.concatenate([h - h[-1], season, [h[-1]]])


def simple_features(w: Well, t: int) -> np.ndarray:
    """Recent head change, level, and season. A gap in the window drops the row."""
    h = w.head[t - LAGS + 1:t + 1]
    recent = h[-1] - h[0] if np.isfinite(h).all() else np.nan
    return np.array([
        recent,
        h[-1],
        np.sin(2 * np.pi * t / 12),
        np.cos(2 * np.pi * t / 12),
    ])


def dataset(wells: list[Well], horizon: int, t0: int, t1: int, feature_fn=features):
    """Rows whose feature window or target is missing are left out, not interpolated."""
    X, y, base = [], [], []
    for w in wells:
        last = min(t1, len(w.head) - horizon)
        for t in range(max(t0, LAGS), last):
            x = feature_fn(w, t)
            target = w.head[t + horizon] - w.head[t]
            if not np.isfinite(x).all() or not np.isfinite(target):
                continue
            X.append(x)
            y.append(target)
            base.append(w.head[t])
    if not X:
        return np.zeros((0, 1)), np.zeros((0,)), np.zeros((0,))
    return np.asarray(X, float), np.asarray(y, float), np.asarray(base, float)


class Forecaster:
    def __init__(self, horizon: int = 6, ridge: float = 1.0, feature_fn=features):
        self.horizon, self.ridge, self.feature_fn = horizon, ridge, feature_fn

    def fit(self, wells, t0, t1):
        X, y, _ = dataset(wells, self.horizon, t0, t1, self.feature_fn)
        if len(y) == 0:
            raise ValueError("no finite training rows")
        self.mean, self.std = X.mean(0), X.std(0) + 1e-9
        Z = np.c_[(X - self.mean) / self.std, np.ones(len(X))]
        if self.ridge == 0:
            self.w = np.linalg.lstsq(Z, y, rcond=None)[0]
        else:
            reg = self.ridge * np.eye(Z.shape[1])
            reg[-1, -1] = 0
            self.w = np.linalg.solve(Z.T @ Z + reg, Z.T @ y)
        return self

    def predict_change(self, X):
        Z = np.c_[(X - self.mean) / self.std, np.ones(len(X))]
        return Z @ self.w


def conformal_halfwidth(fc: Forecaster, wells, t0, t1, alpha: float = 0.1) -> float:
    X, y, _ = dataset(wells, fc.horizon, t0, t1, fc.feature_fn)
    if len(y) == 0:
        raise ValueError("no finite calibration rows")
    residual = np.sort(np.abs(y - fc.predict_change(X)))
    k = int(np.ceil((len(residual) + 1) * (1 - alpha)))
    return float(residual[min(k, len(residual)) - 1])


def coverage_and_error(fc: Forecaster, wells, t0, t1, half: float):
    X, y, _ = dataset(wells, fc.horizon, t0, t1, fc.feature_fn)
    error = np.abs(y - fc.predict_change(X))
    return float(np.mean(error <= half)), float(error.mean())
