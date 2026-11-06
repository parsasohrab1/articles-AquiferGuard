import json
from pathlib import Path

import numpy as np

from aquiferguard.dwr import (
    assign_sites,
    coordinates_trusted,
    good_head_m,
    split_site_ids,
    wells_from_series,
)
from aquiferguard.forecast import dataset, features, head_features, simple_features
from aquiferguard.synth import Well, make_wells


def test_good_head_converts_feet_and_rejects_poor_quality():
    assert abs(good_head_m("1", "10") - 3.048) < 1e-9
    assert abs(good_head_m("10", "1") - 0.3048) < 1e-9
    assert good_head_m("170", "10") is None
    assert good_head_m("1", "") is None


def test_coordinates_follow_the_well_number():
    assert coordinates_trusted("19S23E30A001M", 36.25434, -119.51058, "Tulare")
    assert not coordinates_trusted("13S11E11H003M", 38.8176, -120.73073, "Kings")
    assert coordinates_trusted("02N02W03C001H", 40.589, -124.284, "Humboldt")


def test_colocated_screens_share_a_site_and_a_split():
    def months(level):
        return {f"2001-{m:02d}": level + 0.01 * m for m in range(1, 13)} | {
            f"2002-{m:02d}": level - 0.2 for m in range(1, 13)
        } | {f"2003-{m:02d}": level - 0.4 for m in range(1, 13)}

    series = {
        "A1": months(50.0),
        "A2": months(48.0),
        "B1": months(40.0),
    }
    meta = {
        "A1": {"latitude": 39.0, "longitude": -122.0, "county": "Glenn", "coord_ok": True},
        "A2": {"latitude": 39.0003, "longitude": -122.0, "county": "Glenn", "coord_ok": True},
        "B1": {"latitude": 39.2, "longitude": -122.0, "county": "Glenn", "coord_ok": True},
    }
    wells = wells_from_series(series, meta, min_origins=12)
    by_station = {w.station: w.site_id for w in wells}
    assert by_station["A1"] == by_station["A2"]
    assert by_station["A1"] != by_station["B1"]
    train, cal, test = split_site_ids(sorted(set(by_station.values())), seed=0)
    assert train.isdisjoint(cal) and cal.isdisjoint(test) and train.isdisjoint(test)
    assert train | cal | test == set(by_station.values())
    for left in (train, cal, test):
        assert (by_station["A1"] in left) == (by_station["A2"] in left)


def test_untrusted_coordinates_are_not_merged():
    records = [
        {"station": "A", "latitude": 39.0, "longitude": -122.0, "coord_ok": False},
        {"station": "B", "latitude": 39.0, "longitude": -122.0, "coord_ok": False},
    ]
    sites = assign_sites(records)
    assert sites["A"] != sites["B"]


def test_gaps_are_skipped_and_future_head_is_invisible():
    head = np.arange(40, dtype=float)
    head[20] = np.nan
    well = Well(head, np.zeros(40), np.zeros(40))
    _, y, _ = dataset([well], 6, 0, 40, head_features)
    assert y.size < 40 - 12
    assert np.isfinite(y).all()
    original = head_features(well, 10).copy()
    well.head[11:] += 50
    well.rain[:] = 7
    well.pumping[:] = 9
    assert np.array_equal(original, head_features(well, 10))
    simple = simple_features(well, 10)
    well.displacement = np.ones(40)
    assert np.array_equal(simple, simple_features(well, 10))


def test_synthetic_features_still_ignore_the_future():
    well = make_wells(1, 60, np.random.default_rng(2))[0]
    before = features(well, 30)
    well.head[31:] += 100
    assert np.array_equal(before, features(well, 30))


def test_docs_quote_the_real_run():
    root = Path(__file__).resolve().parents[1]
    results = json.loads((root / "research" / "results.json").read_text(encoding="utf-8"))
    real = results["real"]
    scored = real["test"]
    subsidence = real["subsidence"]
    tokens = [
        f"{scored['mae_ridge_m']:.3f}",
        f"{scored['mae_persistence_m']:.3f}",
        f"{scored['mae_simple_regression_m']:.3f}",
        f"{scored['coverage']:.3f}",
        f"{real['conformal_half_width_m']:.3f}",
        f"{scored['event_rate']:.3f}",
        f"{subsidence['mae_persistence_m']:.3f}",
        f"{subsidence['mae_simple_regression_m']:.3f}",
        f"{subsidence['event_rate']:.3f}",
        f"{subsidence['alert_head_decline']['precision']:.3f}",
        f"{subsidence['alert_head_decline']['recall']:.3f}",
        f"{subsidence['alert_persistence']['precision']:.3f}",
        f"{subsidence['alert_persistence']['recall']:.3f}",
        f"{subsidence['alert_simple_regression']['recall']:.3f}",
    ]
    for name in ("alert_conformal", "alert_point", "alert_trend"):
        tokens.append(f"{scored[name]['precision']:.3f}")
        tokens.append(f"{scored[name]['recall']:.3f}")
    trl = (root / "docs" / "TRL.md").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    for token in tokens[:4]:
        assert token in readme
        assert token in trl
    for token in tokens:
        assert token in trl, token
