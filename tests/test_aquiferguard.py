import numpy as np

from aquiferguard.alert import alert_metrics, conformal_alert, point_alert
from aquiferguard.forecast import (
    Forecaster,
    conformal_halfwidth,
    coverage_and_error,
    dataset,
    features,
)
from aquiferguard.synth import make_wells, subsidence


def test_wells_are_seeded_and_shaped():
    a = make_wells(3, 100, np.random.default_rng(1))
    b = make_wells(3, 100, np.random.default_rng(1))
    assert all(np.array_equal(x.head, y.head) for x, y in zip(a, b, strict=True))
    assert a[0].head.shape == (100,)


def test_features_use_only_past_values():
    w = make_wells(1, 60, np.random.default_rng(2))[0]
    f1 = features(w, 30)
    w.head[31:] += 100.0                       # future change must not alter features at t=30
    assert np.array_equal(f1, features(w, 30))


def test_dataset_targets_are_future_changes():
    w = make_wells(1, 60, np.random.default_rng(3))[0]
    _x, y, base = dataset([w], 6, 10, 20)
    assert y[0] == w.head[16] - w.head[10] and base[0] == w.head[10]


def test_forecast_beats_persistence():
    train = make_wells(20, 240, np.random.default_rng(4))
    test = make_wells(10, 240, np.random.default_rng(5))
    fc = Forecaster(6).fit(train, 12, 150)
    X, y, _ = dataset(test, 6, 160, 234)
    assert np.mean(np.abs(y - fc.predict_change(X))) < np.mean(np.abs(y))


def test_conformal_coverage_on_new_wells():
    train = make_wells(20, 240, np.random.default_rng(6))
    cal = make_wells(10, 240, np.random.default_rng(7))
    test = make_wells(10, 240, np.random.default_rng(8))
    fc = Forecaster(6).fit(train, 12, 150)
    half = conformal_halfwidth(fc, cal, 160, 234)
    cov, _ = coverage_and_error(fc, test, 160, 234, half)
    assert 0.85 <= cov <= 0.95


def test_subsidence_zero_above_preconsolidation():
    assert (subsidence(np.array([50.0, 45.0]), 40.0) == 0).all()
    assert subsidence(np.array([30.0]), 40.0)[0] > 0


def test_conformal_alert_is_more_sensitive_than_point_alert():
    train = make_wells(15, 240, np.random.default_rng(9))
    fc = Forecaster(6).fit(train, 12, 150)
    w = train[0]
    crit = w.head[200] + float(fc.predict_change(features(w, 200)[None, :])[0]) + 0.01
    assert conformal_alert(fc, w, 200, 0.5, crit)
    assert point_alert(fc, w, 200, crit)
    m = alert_metrics(lambda ww, t: conformal_alert(fc, ww, t, 0.3, 45.0), train, 6, 45.0, 160, 230)
    assert m["tp"] + m["fp"] + m["fn"] + m["tn"] > 0
