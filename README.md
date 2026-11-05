# articles-AquiferGuard

Groundwater-level forecasting with calibrated intervals and subsidence-risk alerts. Product for the
IEEE JSTARS special issue "Foundation Models and Multi-Source Remote Sensing for Water Resources"
(remote-sensing data such as InSAR subsidence would be added in the next stage).

**Maturity: TRL 4 on synthetic wells** ([docs/TRL.md](docs/TRL.md)). No monitoring-well or InSAR data yet.

- `src/aquiferguard/synth.py` synthetic wells (recharge, abstraction, regime break), subsidence proxy
- `src/aquiferguard/forecast.py` ridge forecast of head change, split-conformal half-width
- `src/aquiferguard/alert.py` conformal / point / trend alerts and their metrics
- `research/run_study.py` study; `tests/` 7 tests; docs: [BRS](docs/BRS.md) · [SRS](docs/SRS.md) · [TRL](docs/TRL.md)

```bash
pip install -e ".[dev]" && python -m pytest -q && python research/run_study.py
```
