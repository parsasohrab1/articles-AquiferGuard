"""Groundwater forecast and subsidence-alert study on synthetic wells (not field data).

Usage: python research/run_study.py --out research/results.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aquiferguard.alert import (
    alert_metrics,
    conformal_alert,
    point_alert,
    trend_alert,
)
from aquiferguard.forecast import Forecaster, conformal_halfwidth, coverage_and_error
from aquiferguard.synth import make_wells

H, T = 6, 300
TRAIN, CAL, TEST = (12, 160), (160, 220), (220, 290)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="research/results.json")
    a = ap.parse_args()
    train = make_wells(40, T, np.random.default_rng(1))
    cal = make_wells(20, T, np.random.default_rng(2))
    fc = Forecaster(H).fit(train, *TRAIN)
    half = conformal_halfwidth(fc, cal, *CAL)
    out = {"note": "synthetic wells; head change over 6 months; target coverage 0.90",
           "conformal_half_width_m": half}
    crit = lambda w: w.head[0] - 3.0
    settings = {
        "same_regime": make_wells(40, T, np.random.default_rng(3)),
        "abstraction_x1.5_from_month_200": make_wells(
            40, T, np.random.default_rng(3), break_month=200, break_factor=1.5),
    }
    for name, wells in settings.items():
        cov, mae = coverage_and_error(fc, wells, *TEST, half)
        persist = float(np.mean([abs(w.head[t + H] - w.head[t]) for w in wells
                                 for t in range(TEST[0], TEST[1])]))
        out[name] = {
            "coverage": cov, "mae_forecast_m": mae, "mae_persistence_m": persist,
            "alert_conformal": alert_metrics(lambda w, t: conformal_alert(fc, w, t, half, crit(w)),
                                             wells, H, crit, *TEST),
            "alert_point": alert_metrics(lambda w, t: point_alert(fc, w, t, crit(w)),
                                         wells, H, crit, *TEST),
            "alert_trend": alert_metrics(lambda w, t: trend_alert(w, t, H, crit(w)),
                                         wells, H, crit, *TEST)}
    Path(a.out).write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
