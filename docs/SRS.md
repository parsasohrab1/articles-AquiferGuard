# Software Requirements Specification (SRS)

| ID | Requirement | Module | Test |
|----|-------------|--------|------|
| FR-1 | Seeded synthetic wells with recharge, abstraction and an optional regime break | `synth.py` | `test_wells_are_seeded_and_shaped` |
| FR-2 | Predictors use only information available at the forecast time | `forecast.py` | `test_features_use_only_past_values` |
| FR-3 | Training targets are future head changes | `forecast.py` | `test_dataset_targets_are_future_changes` |
| FR-4 | Ridge forecast that beats persistence | `forecast.py` | `test_forecast_beats_persistence` |
| FR-5 | Split-conformal half-width with coverage near the target on new wells | `forecast.py` | `test_conformal_coverage_on_new_wells` |
| FR-6 | Subsidence proxy zero above the preconsolidation head | `synth.py` | `test_subsidence_zero_above_preconsolidation` |
| FR-7 | Conformal, point and trend alerts, with precision and recall | `alert.py` | `test_conformal_alert_is_more_sensitive_than_point_alert` |
| FR-8 | Head-only features ignore future head, rain, pumping and displacement | `forecast.py` | `test_gaps_are_skipped_and_future_head_is_invisible` |
| FR-9 | Good DWR quality codes are converted from feet; other codes are dropped | `dwr.py` | `test_good_head_converts_feet_and_rejects_poor_quality` |
| FR-10 | Co-located screens share a site and therefore a split | `dwr.py` | `test_colocated_screens_share_a_site_and_a_split` |
| FR-11 | A coordinate that disagrees with the state well number is not trusted | `dwr.py` | `test_coordinates_follow_the_well_number` |

Assumptions for the synthetic path: head follows a linear recharge/abstraction balance with noise; the synthetic subsidence proxy is proportional to head decline below the preconsolidation head (compressibility 0.01 m per m); the synthetic critical head is 3 m below the initial head. The real-well path does not use that proxy. It forecasts from past heads only, and it scores displacement from the published TRE Altamira series.
