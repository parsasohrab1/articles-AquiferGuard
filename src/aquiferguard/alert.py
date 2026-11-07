"""Subsidence-risk alerts from the forecast interval."""

from __future__ import annotations

import numpy as np

from .forecast import Forecaster
from .synth import Well


def _predicted_head(fc: Forecaster, w: Well, t: int) -> float:
    change = float(fc.predict_change(fc.feature_fn(w, t)[None, :])[0])
    return float(w.head[t] + change)


def conformal_alert(fc: Forecaster, w: Well, t: int, half: float, critical_head: float) -> bool:
    """Alert when the lower bound of the forecast head is below the critical head."""
    return _predicted_head(fc, w, t) - half < critical_head


def point_alert(fc: Forecaster, w: Well, t: int, critical_head: float) -> bool:
    return _predicted_head(fc, w, t) < critical_head


def trend_alert(w: Well, t: int, horizon: int, critical_head: float, window: int = 12) -> bool:
    slope = np.polyfit(np.arange(window), w.head[t - window + 1:t + 1], 1)[0]
    return w.head[t] + slope * horizon < critical_head


def alert_metrics(fn, wells, horizon: int, critical_head, t0: int, t1: int) -> dict:
    """`critical_head` is a number or a function of the well."""
    tp = fp = fn_ = tn = 0
    for w in wells:
        crit = critical_head(w) if callable(critical_head) else critical_head
        for t in range(t0, min(t1, len(w.head) - horizon)):
            truth = w.head[t + horizon] < crit
            pred = fn(w, t)
            truth, pred = bool(truth), bool(pred)
            tp += int(truth and pred)
            fp += int((not truth) and pred)
            fn_ += int(truth and (not pred))
            tn += int((not truth) and (not pred))
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn_) if tp + fn_ else float("nan")
    return {"precision": float(prec), "recall": float(rec), "tp": tp, "fp": fp, "fn": fn_, "tn": tn}
