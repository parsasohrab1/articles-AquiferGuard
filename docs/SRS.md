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

Assumptions: head follows a linear recharge/abstraction balance with noise; subsidence is proportional to head decline below the preconsolidation head (compressibility 0.01 m per m); the critical head is 3 m below the initial head.
