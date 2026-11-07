# Journal fitness — IEEE J-STARS

Call checked: special issue "Foundation Models and Multi-Source Remote Sensing for Water Resources Monitoring, Assessment, and Management".

| Item | Record |
|---|---|
| Call page | https://www.grss-ieee.org/wp-content/uploads/2026/08/JSTARS_CfP_Foundation-Models-and-Muli-Source-Remote-Sensing.pdf |
| Listing | https://www.grss-ieee.org/publications/author-resources/call-for-papers/ |
| Journal | IEEE Journal of Selected Topics in Applied Earth Observations and Remote Sensing |
| Submission opens | 1 September 2026 |
| Submission closes | 30 April 2027 |
| Checked | 7 November 2026 |

| Item | What the call page says |
|---|---|
| Scope | Remote sensing, multi-source data fusion, and geospatial foundation models for water resources. Named topics include optical, SAR, thermal, LiDAR, UAV and in situ fusion, and groundwater-related indicators from Earth observation. |
| Article types | Original research and review papers, IEEE two-column format, submitted in Manuscript Central under this special-issue type. |
| Deadline | The listing shows the submission window open from 1 September 2026 through 30 April 2027. |

## Fit

The call names groundwater-related indicators and in situ data, so the topic touches this repository. The method it asks for does not. The study in `research/results.json` is a ridge regression on past well heads, an ordinary regression, and persistence, with a split-conformal interval. TRE Altamira displacement is an evaluation label. It is not a model input. There is no foundation model and no multi-source fusion.

On the held-out wells the ridge MAE is 1.518 m, against 2.881 m for persistence and 1.563 m for ordinary regression. Coverage of the 0.90 interval is 0.858. The subsidence warning is not supported: 12 events in 2203 origins, and the head-decline alert precision is 0.012.

## Decision

Do not submit. No file has been uploaded.

The window is open on the day of this check. Submission stays closed anyway. The manuscript would not be a remote-sensing or foundation-model paper, the 0.90 interval does not hold, and a patent attorney has not confirmed that the text to be sent discloses no claimed method. The note in [../article/abstract.md](../article/abstract.md) is not a submission. The internal filing card is [REGISTRATION.md](REGISTRATION.md).
