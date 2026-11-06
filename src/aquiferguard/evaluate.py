"""Synthetic study and the real-well study.

The real split keeps every well, and every co-located screen, on one side only.
A decline event is a 6-month head drop of more than DECLINE_M (1 m), fixed before
looking at test scores. A subsidence event is an additional downward displacement
of at least SUBSIDENCE_M (3 cm) over six months, above the published long-period
InSAR accuracy.
"""

from __future__ import annotations

import math

import numpy as np

from .alert import alert_metrics, conformal_alert, point_alert, trend_alert
from .dwr import split_site_ids
from .forecast import (
    LAGS,
    Forecaster,
    conformal_halfwidth,
    coverage_and_error,
    dataset,
    head_features,
    simple_features,
)
from .synth import Well, make_wells

HORIZON = 6
DECLINE_M = 1.0
SUBSIDENCE_M = 0.03
SPLIT_SEED = 0


def _clean(value):
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return None if not math.isfinite(number) else number
    if isinstance(value, (np.integer,)):
        return int(value)
    return value


def _counts(truth: np.ndarray, pred: np.ndarray) -> dict:
    tp = int(np.sum(truth & pred))
    fp = int(np.sum(~truth & pred))
    fn = int(np.sum(truth & ~pred))
    tn = int(np.sum(~truth & ~pred))
    precision = tp / (tp + fp) if tp + fp else float("nan")
    recall = tp / (tp + fn) if tp + fn else float("nan")
    return {"precision": precision, "recall": recall, "tp": tp, "fp": fp, "fn": fn, "tn": tn}


def run_synthetic() -> dict:
    """The original synthetic-well study, kept so the TRL 4 numbers stay reproducible."""
    t_len = 300
    train_window, cal_window, test_window = (12, 160), (160, 220), (220, 290)
    train = make_wells(40, t_len, np.random.default_rng(1))
    cal = make_wells(20, t_len, np.random.default_rng(2))
    forecaster = Forecaster(HORIZON).fit(train, *train_window)
    half = conformal_halfwidth(forecaster, cal, *cal_window)
    out = {
        "note": "synthetic wells; head change over 6 months; target coverage 0.90",
        "conformal_half_width_m": half,
    }
    critical = lambda w: w.head[0] - 3.0
    settings = {
        "same_regime": make_wells(40, t_len, np.random.default_rng(3)),
        "abstraction_x1.5_from_month_200": make_wells(
            40, t_len, np.random.default_rng(3), break_month=200, break_factor=1.5),
    }
    for name, wells in settings.items():
        coverage, mae = coverage_and_error(forecaster, wells, *test_window, half)
        persist = float(np.mean([
            abs(w.head[t + HORIZON] - w.head[t])
            for w in wells for t in range(test_window[0], test_window[1])
        ]))
        out[name] = {
            "coverage": coverage,
            "mae_forecast_m": mae,
            "mae_persistence_m": persist,
            "alert_conformal": alert_metrics(
                lambda w, t: conformal_alert(forecaster, w, t, half, critical(w)),
                wells, HORIZON, critical, *test_window),
            "alert_point": alert_metrics(
                lambda w, t: point_alert(forecaster, w, t, critical(w)),
                wells, HORIZON, critical, *test_window),
            "alert_trend": alert_metrics(
                lambda w, t: trend_alert(w, t, HORIZON, critical(w)),
                wells, HORIZON, critical, *test_window),
        }
    return _clean(out)


def _partition(wells: list[Well]):
    train_sites, cal_sites, test_sites = split_site_ids(
        sorted({w.site_id for w in wells}), seed=SPLIT_SEED)
    def take(sites):
        return [w for w in wells if w.site_id in sites]
    return take(train_sites), take(cal_sites), take(test_sites), train_sites, cal_sites, test_sites


def _decline_alerts(forecaster: Forecaster, wells: list[Well], half: float) -> dict:
    truth, conformal, point, trend = [], [], [], []
    window = 12
    for well in wells:
        last = len(well.head) - HORIZON
        for t in range(max(LAGS, window - 1), last):
            block = well.head[t - window + 1:t + 1]
            future = well.head[t + HORIZON]
            if not np.isfinite(block).all() or not np.isfinite(future):
                continue
            critical = float(well.head[t] - DECLINE_M)
            truth.append(future < critical)
            conformal.append(conformal_alert(forecaster, well, t, half, critical))
            point.append(point_alert(forecaster, well, t, critical))
            trend.append(trend_alert(well, t, HORIZON, critical))
    truth_a = np.asarray(truth, dtype=bool)
    return {
        "n_origins": int(truth_a.size),
        "event_rate": float(truth_a.mean()) if truth_a.size else float("nan"),
        "alert_conformal": _counts(truth_a, np.asarray(conformal, dtype=bool)),
        "alert_point": _counts(truth_a, np.asarray(point, dtype=bool)),
        "alert_trend": _counts(truth_a, np.asarray(trend, dtype=bool)),
    }


def _representatives(wells: list[Well]) -> list[Well]:
    best: dict[str, Well] = {}
    for well in wells:
        if well.displacement is None or not np.isfinite(well.displacement).any():
            continue
        current = best.get(well.site_id)
        n_finite = int(np.isfinite(well.head).sum())
        if current is None:
            best[well.site_id] = well
            continue
        current_n = int(np.isfinite(current.head).sum())
        if n_finite > current_n or (n_finite == current_n and well.station < current.station):
            best[well.site_id] = well
    return [best[k] for k in sorted(best)]


def _subsidence_rows(wells: list[Well]):
    frames = []
    for well in wells:
        disp = well.displacement
        last = len(well.head) - HORIZON
        for t in range(max(LAGS, HORIZON), last):
            dh = well.head[t] - well.head[t - HORIZON]
            dd = disp[t] - disp[t - HORIZON]
            future = disp[t + HORIZON] - disp[t]
            features = head_features(well, t)
            if not np.isfinite(features).all() or not np.isfinite([dh, dd, future]).all():
                continue
            frames.append((dh, dd, future, features))
    if not frames:
        empty = np.zeros((0,))
        return empty, empty, empty, np.zeros((0, 1))
    dh, dd, future, features = zip(*frames, strict=True)
    return (np.asarray(dh, float), np.asarray(dd, float), np.asarray(future, float),
            np.asarray(features, float))


def _subsidence_block(train: list[Well], test: list[Well], forecaster: Forecaster) -> dict:
    train_rep, test_rep = _representatives(train), _representatives(test)
    dh_tr, dd_tr, y_tr, _ = _subsidence_rows(train_rep)
    dh_te, dd_te, y_te, x_te = _subsidence_rows(test_rep)
    block = {
        "available": bool(y_te.size and y_tr.size),
        "n_train_sites": len(train_rep),
        "n_test_sites": len(test_rep),
        "n_origins": int(y_te.size),
    }
    if not block["available"]:
        block["reason"] = "no overlapping groundwater and InSAR origins on held-out sites"
        return block
    design = np.c_[dh_tr, dd_tr, np.ones(len(y_tr))]
    coef = np.linalg.lstsq(design, y_tr, rcond=None)[0]
    predicted = np.c_[dh_te, dd_te, np.ones(len(y_te))] @ coef
    event = y_te <= -SUBSIDENCE_M
    head_change = forecaster.predict_change(x_te)
    block.update({
        "event_rate": float(event.mean()),
        "mae_persistence_m": float(np.mean(np.abs(y_te - dd_te))),
        "mae_simple_regression_m": float(np.mean(np.abs(y_te - predicted))),
        "alert_persistence": _counts(event, dd_te <= -SUBSIDENCE_M),
        "alert_simple_regression": _counts(event, predicted <= -SUBSIDENCE_M),
        "alert_head_decline": _counts(event, head_change <= -DECLINE_M),
    })
    return block


def run_real(wells: list[Well], manifest: dict | None = None) -> dict:
    train, cal, test, train_sites, cal_sites, test_sites = _partition(wells)
    t1 = max(len(w.head) for w in wells) + 1
    ridge = Forecaster(HORIZON, ridge=1.0, feature_fn=head_features).fit(train, 0, t1)
    simple = Forecaster(HORIZON, ridge=0.0, feature_fn=simple_features).fit(train, 0, t1)
    half = conformal_halfwidth(ridge, cal, 0, t1)
    x_test, y_test, _ = dataset(test, HORIZON, 0, t1, head_features)
    ridge_mae = float(np.mean(np.abs(y_test - ridge.predict_change(x_test))))
    # simple_features is finite on the same months as head_features.
    x_simple, y_simple, _ = dataset(test, HORIZON, 0, t1, simple_features)
    if y_simple.shape != y_test.shape or not np.allclose(y_simple, y_test):
        raise RuntimeError("simple regression is not scored on the same origins as ridge")
    simple_mae = float(np.mean(np.abs(y_simple - simple.predict_change(x_simple))))
    persist_mae = float(np.mean(np.abs(y_test)))
    coverage = float(np.mean(np.abs(y_test - ridge.predict_change(x_test)) <= half))
    alerts = _decline_alerts(ridge, test, half)
    counties: dict[str, int] = {}
    for well in wells:
        counties[well.county or "unknown"] = counties.get(well.county or "unknown", 0) + 1
    info = manifest or {}
    out = {
        "note": (
            "DWR continuous monthly groundwater elevation, meters, 6-month head change. "
            "Split by well site (co-located screens stay together). "
            "InSAR is an evaluation label, not a model input. "
            "No foundation model."
        ),
        "groundwater_source": info.get(
            "groundwater_source",
            "California DWR Continuous Groundwater Level Measurements, monthly mean"),
        "groundwater_url": info.get("groundwater_url", ""),
        "insar_source": info.get(
            "insar_source",
            "DWR TRE ALTAMIRA cumulative vertical displacement since 2015-06-13"),
        "insar_url": info.get("insar_url", ""),
        "retrieved": info.get("retrieved", ""),
        "insar_failed_dates": info.get("insar_failed_dates", []),
        "units": "meters",
        "horizon_months": HORIZON,
        "split": "well_site",
        "seed": SPLIT_SEED,
        "decline_event_m": DECLINE_M,
        "subsidence_event_m": SUBSIDENCE_M,
        "min_origins": 24,
        "n_wells": len(wells),
        "n_sites": len({w.site_id for w in wells}),
        "n_train_wells": len(train),
        "n_cal_wells": len(cal),
        "n_test_wells": len(test),
        "n_train_sites": len(train_sites),
        "n_cal_sites": len(cal_sites),
        "n_test_sites": len(test_sites),
        "n_wells_without_trusted_coordinates": sum(not w.coord_ok for w in wells),
        "counties": dict(sorted(counties.items())),
        "conformal_half_width_m": half,
        "test": {
            "n_origins": int(y_test.size),
            "coverage": coverage,
            "mae_ridge_m": ridge_mae,
            "mae_persistence_m": persist_mae,
            "mae_simple_regression_m": simple_mae,
            **alerts,
        },
        "subsidence": _subsidence_block(train, test, ridge),
    }
    return _clean(out)
