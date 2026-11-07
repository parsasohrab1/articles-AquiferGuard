# Technology readiness (evidence-based)

**Level: TRL 4.** TRL 5 is not claimed. The 6-month head forecast has now been run on real monitoring wells and beats both baselines below. The 90 percent interval does not hold on those wells, and the subsidence warning does not either.

Numbers below are the study script's output rounded to three decimals. Full precision is in [research/results.json](../research/results.json), which `python research/run_study.py --check` regenerates.

## Real wells

Snapshot retrieved 2026-11-06.

- Groundwater: California DWR continuous monthly mean water-surface elevation (quality codes 1, 2 and 10), feet converted with 0.3048. Wells need at least 24 complete 6-month origins. Missing months are skipped, not interpolated.
- 462 wells at 183 sites. Co-located screens within 200 m stay in the same split. The hash split (seed 0) puts 91 sites in training, 45 in calibration and 47 in test (232 / 114 / 116 wells).
- The network is mostly the Sacramento Valley: Glenn 87, Butte 60, Yolo 58, Tehama 54, Sutter 53, Colusa 32, Solano 28, San Joaquin 24, and smaller counts elsewhere. It is not a sample of the San Joaquin subsidence bowl.
- Head model inputs are past heads and the month of the year. Rainfall and pumping are not in this table, and InSAR is not a model input.
- InSAR: DWR's public TRE Altamira image services, cumulative vertical displacement since 2015-06-13, read at the site and converted from feet. 150 of 183 sites returned a finite pixel. The warning uses one well per site, the one with the longest head record.
- A decline event is a drop of more than 1 m within six months. A subsidence event is at least 3 cm of further downward displacement within six months. Both thresholds were fixed before the test scores.

6-month head change on the 7960 test origins. The conformal half-width, fit on the calibration wells, is 2.666 m.

| Model | MAE (m) | Coverage (target 0.90) |
|---|---|---|
| Ridge on past heads | 1.518 | 0.858 |
| Ordinary regression (recent change, level, season) | 1.563 |  |
| Persistence (no change) | 2.881 |  |

Alerts for a drop of more than 1 m. The event rate on this sample is 0.284.

| Alert rule | Precision | Recall |
|---|---|---|
| Conformal lower bound | 0.370 | 0.986 |
| Point forecast | 0.644 | 0.874 |
| Linear trend | 0.311 | 0.250 |

The half-width (2.666 m) is wider than the 1 m decline, so the lower bound sits below the threshold unless the point forecast is a large rise. That is why the conformal rule recalls 0.986 of the declines and is right only 0.370 of the time. The point forecast is the better of the three rules. The linear trend is weak.

Subsidence on 41 held-out sites with InSAR (2203 origins). The event rate is 0.005 (12 origins).

| Displacement forecast | MAE (m) |
|---|---|
| Ordinary regression on the recent head change and the recent displacement change | 0.005 |
| Persistence of the recent displacement change | 0.014 |

| Warning, scored against the 3 cm displacement event | Precision | Recall |
|---|---|---|
| Persistence of the recent displacement change | 0.000 | 0.000 |
| Ordinary regression | no alerts | 0.000 |
| Head-decline point forecast (drop of more than 1 m) | 0.012 | 0.917 |

The regression is closer to the observed displacement change than persistence is, and it never reaches the 3 cm line, so it issues no warning. The head-decline rule catches 11 of the 12 displacement events and raises 936 false alarms. On this network a 1 m head drop is not a subsidence warning.

## Synthetic wells

The synthetic study is unchanged and is still produced by the same script.

7 of the unit tests cover that path. `research/run_study.py` (train 40 wells, calibrate 20 wells, test 40 wells; 6-month horizon; 300 months):

| Test setting | Coverage (target 0.90) | Forecast MAE (m) | Persistence MAE (m) |
|---|---|---|---|
| Same regime | 0.918 | 0.129 | 0.268 |
| Abstraction x1.5 from month 200 | 0.848 | 0.152 | 0.356 |

Alerts for "head below initial head minus 3 m within six months":

| Setting | Alert rule | Precision | Recall |
|---|---|---|---|
| Same regime | Conformal lower bound | 0.85 | 1.00 |
| Same regime | Point forecast | 0.96 | 0.98 |
| Same regime | Linear trend | 0.91 | 0.93 |
| Abstraction x1.5 | Conformal lower bound | 0.95 | 1.00 |
| Abstraction x1.5 | Point forecast | 0.99 | 0.98 |
| Abstraction x1.5 | Linear trend | 0.97 | 0.97 |

On synthetic wells from the same linear family the forecaster fits, the conformal alert does not miss a same-regime event. Coverage falls after the regime break. Those wells are not the DWR result above.

## Not claimed

- TRL 5. There is no operational trial, the 90 percent interval misses on new wells (0.858), and the subsidence warning is not precise.
- A foundation model, or a multi-source remote-sensing model. InSAR is an external label. The JSTARS special issue remains out of scope, and no article is submitted.
- Methods that are the subject of a patent filing. This repository evaluates ridge regression, ordinary least squares, persistence and split-conformal intervals only.
- A spatial block. Neighboring sites can sit on opposite sides of the split, so the head-forecast gain can be helped by spatial correlation.
- Skill in the San Joaquin subsidence bowl. This continuous-recorder network barely includes it, which is why a 3 cm movement in six months is rare here.
