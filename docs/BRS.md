# Business Requirements Specification (BRS)

**Product:** AquiferGuard (basket id `aquiferguard`). Written from the basket description and this code; not reviewed by the owner.

## Business problem
Falling groundwater levels and land subsidence in Iranian plains (Tehran, Isfahan, Rafsanjan) damage infrastructure. Regional water companies need a forecast with an honest uncertainty and an alert rule they can defend.

## Objectives
| ID | Objective |
|----|-----------|
| BO-1 | Forecast head six months ahead for each monitoring well |
| BO-2 | Attach an interval of stated coverage and say when coverage degrades after a regime change |
| BO-3 | Alert on the chance of crossing a critical head, with the precision/recall trade-off visible |
| BO-4 | Compare with simple baselines (persistence, linear trend) |

## Users
Regional water companies, the Ministry of Energy, geological survey.

## Scope
In: head forecasting and alerts per well, subsidence proxy. Out: InSAR processing, spatial interpolation, abstraction scenarios, a full groundwater flow model.

## Success measures (on real wells)
Forecast error vs persistence, interval coverage, alert precision and recall on held-out wells and years.
