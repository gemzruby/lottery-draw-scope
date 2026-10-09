# Sampling stability experiment

Round: `645_1503_091026`.

The 10-, 30-, and 100-run checkpoints are nested prefixes of the same round.
All runs use the same development and holdout dates. The data are exploratory,
not an unseen independent test set.

| Runs | First main combination | Main hits | Baseline | Difference | Seed SD |
| --- | --- | --- | --- | --- | --- |
| 10 | 03 07 19 33 36 43 | 0.795 | 0.782 | +0.013 | 0.100 |
| 30 | 03 06 07 16 19 36 | 0.775 | 0.787 | -0.012 | 0.076 |
| 100 | 03 06 16 31 36 45 | 0.761 | 0.796 | -0.035 | 0.093 |

## Changes between checkpoints

| Change | Main numbers retained | Distribution TV | Configuration TV |
| --- | --- | --- | --- |
| 10 to 30 | 4 | 0.256 | 0.167 |
| 30 to 100 | 4 | 0.131 | 0.127 |

Total variation (TV) ranges from 0 to 1; smaller values indicate closer distributions.
Seed SD is descriptive spread across runs, not statistical uncertainty in future draws.
The boundary margin and full configuration counts are in comparison.json.
A stable consensus does not imply improved winning probabilities.

[Comparison JSON](../backtests/645/645_1503_091026/comparison.json).
