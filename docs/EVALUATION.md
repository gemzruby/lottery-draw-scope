# Latest round evaluation

Round: `655_1446_091026` (Asia/Ho_Chi_Minh).

Ten runs evaluated predict and simulate across windows 30, 60, 120, and all history.
Each run used one different seed offset and 1,000 samples per simulation target.
The strategy and window were selected on development targets before scoring the final holdout.

| Run | Strategy | Window | Main hits | Baseline |
| --- | --- | --- | --- | --- |
| 1 | simulate | 30 | 0.633 | 0.683 |
| 2 | simulate | 30 | 0.683 | 0.800 |
| 3 | simulate | 30 | 0.633 | 0.467 |
| 4 | simulate | 30 | 0.617 | 0.817 |
| 5 | simulate | 30 | 0.567 | 0.683 |
| 6 | simulate | 30 | 0.683 | 0.517 |
| 7 | simulate | 30 | 0.600 | 0.617 |
| 8 | simulate | 30 | 0.683 | 0.617 |
| 9 | simulate | 30 | 0.733 | 0.633 |
| 10 | simulate | 30 | 0.617 | 0.667 |

Mean holdout main hits: 0.645; baseline: 0.650.

## Consensus suggestions

- Rank 1: 05 07 11 18 25 27 15; main consensus score 52.
- Rank 2: 05 07 11 18 25 38 15; main consensus score 50.

Consensus counts appearances in the ten per-run suggestions. Holdout scores do not
weight this ranking. It does not represent winning probabilities or demonstrate
superiority to random selection. All runs reuse the same data; earlier backtests
already inspected this history. This remains exploratory.

[Suggestion JSON](../backtests/suggestions/655_1446_091026.json).
