# Latest round evaluation

Round: `645_1503_091026` (Asia/Ho_Chi_Minh).

100 runs evaluated predict and simulate across windows 30, 60, 120, and all history.
Each run used one different seed offset and 1,000 samples per simulation target.
The strategy and window were selected on development targets before scoring the final holdout.

| Run | Strategy | Window | Main hits | Baseline |
| --- | --- | --- | --- | --- |
| 1 | simulate | 0 | 0.767 | 0.667 |
| 2 | simulate | 60 | 0.800 | 0.850 |
| 3 | predict | 0 | 0.667 | 0.783 |
| 4 | predict | 120 | 0.750 | 0.767 |
| 5 | simulate | 0 | 0.867 | 0.567 |
| 6 | predict | 120 | 0.667 | 0.917 |
| 7 | predict | 0 | 0.767 | 0.850 |
| 8 | predict | 30 | 1.000 | 0.717 |
| 9 | predict | 30 | 0.917 | 0.883 |
| 10 | predict | 120 | 0.750 | 0.817 |
| 11 | simulate | 0 | 0.617 | 0.683 |
| 12 | simulate | 120 | 0.800 | 0.700 |
| 13 | simulate | 120 | 0.750 | 0.683 |
| 14 | predict | 120 | 0.767 | 0.833 |
| 15 | simulate | 0 | 0.750 | 0.850 |
| 16 | predict | 30 | 0.717 | 0.667 |
| 17 | predict | 60 | 0.783 | 0.767 |
| 18 | simulate | 0 | 0.783 | 0.983 |
| 19 | predict | 60 | 0.817 | 0.867 |
| 20 | predict | 120 | 0.800 | 0.883 |
| 21 | simulate | 60 | 0.783 | 0.733 |
| 22 | predict | 0 | 0.733 | 0.733 |
| 23 | simulate | 60 | 0.817 | 0.683 |
| 24 | predict | 120 | 0.900 | 0.850 |
| 25 | predict | 0 | 0.733 | 0.817 |
| 26 | simulate | 0 | 0.683 | 0.783 |
| 27 | simulate | 0 | 0.717 | 0.767 |
| 28 | predict | 30 | 0.800 | 0.867 |
| 29 | predict | 0 | 0.750 | 0.783 |
| 30 | predict | 30 | 0.800 | 0.850 |
| 31 | predict | 60 | 0.717 | 0.817 |
| 32 | predict | 30 | 0.850 | 0.867 |
| 33 | simulate | 0 | 0.517 | 0.783 |
| 34 | simulate | 0 | 0.683 | 0.933 |
| 35 | predict | 30 | 0.833 | 0.750 |
| 36 | predict | 0 | 0.750 | 0.733 |
| 37 | predict | 0 | 0.850 | 0.733 |
| 38 | simulate | 120 | 0.850 | 0.767 |
| 39 | predict | 30 | 0.933 | 0.650 |
| 40 | predict | 60 | 0.750 | 0.867 |
| 41 | simulate | 60 | 0.650 | 0.933 |
| 42 | simulate | 30 | 0.700 | 0.683 |
| 43 | predict | 120 | 0.867 | 0.917 |
| 44 | simulate | 60 | 0.667 | 0.833 |
| 45 | predict | 60 | 0.800 | 0.783 |
| 46 | simulate | 120 | 0.767 | 0.800 |
| 47 | predict | 30 | 0.750 | 0.817 |
| 48 | simulate | 60 | 0.783 | 0.767 |
| 49 | simulate | 0 | 0.733 | 0.850 |
| 50 | simulate | 0 | 0.767 | 0.650 |
| 51 | predict | 0 | 0.833 | 0.583 |
| 52 | predict | 120 | 0.817 | 0.617 |
| 53 | simulate | 60 | 0.833 | 0.683 |
| 54 | predict | 120 | 0.783 | 0.783 |
| 55 | simulate | 0 | 0.567 | 0.700 |
| 56 | simulate | 60 | 0.833 | 1.017 |
| 57 | predict | 30 | 0.783 | 0.900 |
| 58 | simulate | 60 | 0.800 | 0.700 |
| 59 | predict | 60 | 0.750 | 0.833 |
| 60 | simulate | 0 | 0.650 | 1.133 |
| 61 | simulate | 0 | 0.700 | 0.833 |
| 62 | simulate | 60 | 0.783 | 0.783 |
| 63 | predict | 120 | 0.950 | 0.767 |
| 64 | simulate | 60 | 0.767 | 0.767 |
| 65 | predict | 0 | 0.817 | 0.883 |
| 66 | simulate | 60 | 0.783 | 0.817 |
| 67 | predict | 60 | 0.900 | 1.000 |
| 68 | simulate | 0 | 0.800 | 0.800 |
| 69 | simulate | 0 | 0.700 | 0.800 |
| 70 | predict | 30 | 0.767 | 0.850 |
| 71 | simulate | 60 | 0.767 | 0.867 |
| 72 | predict | 30 | 0.533 | 0.633 |
| 73 | simulate | 0 | 0.717 | 0.933 |
| 74 | simulate | 0 | 0.583 | 0.867 |
| 75 | simulate | 60 | 0.733 | 0.683 |
| 76 | predict | 0 | 0.750 | 0.850 |
| 77 | predict | 0 | 0.717 | 0.683 |
| 78 | predict | 30 | 0.667 | 0.850 |
| 79 | simulate | 60 | 0.683 | 0.850 |
| 80 | predict | 0 | 0.850 | 0.783 |
| 81 | simulate | 120 | 0.717 | 0.700 |
| 82 | simulate | 0 | 0.500 | 0.817 |
| 83 | predict | 60 | 0.750 | 0.767 |
| 84 | predict | 0 | 0.900 | 0.767 |
| 85 | predict | 120 | 0.683 | 0.583 |
| 86 | predict | 60 | 0.967 | 0.667 |
| 87 | predict | 0 | 0.733 | 0.800 |
| 88 | simulate | 60 | 0.817 | 0.717 |
| 89 | simulate | 120 | 0.850 | 0.983 |
| 90 | predict | 120 | 0.667 | 0.883 |
| 91 | simulate | 0 | 0.617 | 1.167 |
| 92 | simulate | 60 | 0.733 | 0.783 |
| 93 | predict | 0 | 0.783 | 0.667 |
| 94 | simulate | 120 | 0.817 | 0.983 |
| 95 | predict | 60 | 0.883 | 0.550 |
| 96 | predict | 30 | 0.833 | 0.800 |
| 97 | predict | 60 | 0.833 | 0.883 |
| 98 | simulate | 0 | 0.533 | 0.750 |
| 99 | predict | 30 | 0.683 | 0.867 |
| 100 | predict | 120 | 0.733 | 0.733 |

Mean holdout main hits: 0.761; baseline: 0.796.

## Consensus suggestions

- Rank 1: 03 06 16 31 36 45; main consensus score 173.
- Rank 2: 03 06 16 27 31 36; main consensus score 172.

Consensus counts appearances in the per-run suggestions. Holdout scores do not
weight this ranking. It does not represent winning probabilities or demonstrate
superiority to random selection. All runs reuse the same data; earlier backtests
already inspected this history. This remains exploratory.

[Suggestion JSON](../backtests/suggestions/645_1503_091026.json).
