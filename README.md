# articles-AquiferGuard

Groundwater-level forecasting with calibrated intervals, scored against persistence and ordinary least squares. The IEEE JSTARS special issue on foundation models and multi-source remote sensing is not a fit for this repository, and no article is submitted from this branch. The code uses ridge regression, ordinary least squares, persistence, and split-conformal intervals. It does not describe methods that are the subject of a patent filing.

**Maturity: TRL 4** ([docs/TRL.md](docs/TRL.md)). On held-out California DWR wells the 6-month ridge MAE is **1.518 m**, against **2.881 m** for persistence and **1.563 m** for ordinary regression. Coverage of the 90 percent interval is **0.858**. The subsidence warning is not supported.

- `data/wells_monthly.csv` — DWR continuous monthly water-surface elevation, quality codes 1, 2 and 10, converted from feet
- `data/insar_monthly.csv` — TRE Altamira cumulative vertical displacement since 2015-06-13, sampled at the well sites
- `src/aquiferguard/forecast.py` — ridge and ordinary-regression forecasts, split-conformal half-width
- `src/aquiferguard/alert.py` — conformal, point and trend alerts
- `research/run_study.py` writes `research/results.json`; `research/fetch_real.py` refreshes the snapshot

```bash
pip install -e ".[dev]"
python -m ruff check src tests research
python -m pytest -q
python research/run_study.py --check
```
