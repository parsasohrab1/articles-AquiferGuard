# Abstract

Six-month groundwater-head changes were forecast for monitoring wells in the California Department of Water Resources continuous monthly record (quality codes 1, 2 and 10, converted from feet to meters). Co-located screens within 200 m share a site, and whole sites are held out. The test split has 116 wells at 47 sites and 7960 origins. Predictors are past heads and the month of the year. Rainfall, pumping, and satellite displacement are not inputs.

A ridge regression has mean absolute error 1.518 m. An ordinary regression on the recent change, the level, and the season has 1.563 m. Persistence has 2.881 m. A split-conformal interval aimed at coverage 0.90 has half-width 2.666 m and coverage 0.858 on the held-out wells. For a drop of more than 1 m (event rate 0.284), the conformal lower bound has precision 0.370 and recall 0.986, the point forecast has precision 0.644 and recall 0.874, and a linear trend has precision 0.311 and recall 0.250.

TRE Altamira cumulative vertical displacement since 13 June 2015, published by DWR, is used only as a label at the well site. On 41 test sites and 2203 origins, a further downward movement of at least 3 cm in six months occurs at rate 0.005 (12 origins). Persistence of the recent displacement change has error 0.014 m and precision 0.000, recall 0.000. An ordinary regression on the recent head change and the recent displacement change has error 0.005 m, issues no alert, and has recall 0.000. Alerting when the head forecast drops by more than 1 m has precision 0.012 and recall 0.917. That rule is not a subsidence warning on this network.

This note is not submitted. The IEEE J-STARS special issue on foundation models and multi-source remote sensing is a different kind of paper, and a patent attorney has not reviewed this text. It describes only ridge regression, ordinary least squares, persistence, and a split-conformal interval.

Numbers are rounded from `research/results.json`, which `python research/run_study.py` writes. They were not entered by hand.
