# Sampling stability experiment

Round: `655_2004_091026`.

The 20, 50, 200-run checkpoints are nested prefixes of the same round.
All runs use the same development and holdout dates. The data are exploratory,
not an unseen independent test set.

| Runs | First combination (bonus last if applicable) | Main hits | Baseline | Difference | Seed SD |
| --- | --- | --- | --- | --- | --- |
| 20 | 05 07 11 18 25 27 15 | 0.662 | 0.656 | +0.007 | 0.046 |
| 50 | 05 07 11 18 25 27 31 | 0.654 | 0.650 | +0.004 | 0.046 |
| 200 | 05 07 11 18 25 27 11 | 0.643 | 0.650 | -0.007 | 0.058 |

## Changes between checkpoints

| Change | Main numbers retained | Distribution TV | Configuration TV |
| --- | --- | --- | --- |
| 20 to 50 | 6 | 0.095 | 0.100 |
| 50 to 200 | 6 | 0.081 | 0.035 |

## Final consensus combinations

| Rank | Main numbers | Bonus | Consensus score |
| --- | --- | --- | --- |
| 1 | 05 07 11 18 25 27 | 11 | 950 |
| 2 | 05 07 11 14 18 27 | 11 | 846 |
| 3 | 07 11 14 18 25 27 | 11 | 844 |
| 4 | 01 05 07 11 18 27 | 11 | 843 |
| 5 | 01 07 11 18 25 27 | 11 | 841 |

Total variation (TV) ranges from 0 to 1; smaller values indicate closer distributions.
Seed SD is descriptive spread across runs, not statistical uncertainty in future draws.
The boundary margin and full configuration counts are in comparison.json.
A stable consensus does not imply improved winning probabilities.

[Comparison JSON](../backtests/655/655_2004_091026/comparison.json).
