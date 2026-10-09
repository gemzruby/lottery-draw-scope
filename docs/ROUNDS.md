# Backtest rounds

```bash
make round PRODUCT=645 SAMPLES=1000 WORKERS=2
```

One round runs ten numbered iterations by default (`RUNS` changes the count) for a single product. `make evaluate`
is an alias for `make round`. Use `PRODUCT=535` or `PRODUCT=655` for another
product. `WORKERS` defaults to 2 and accepts 1 through 4. The base seed is derived
from the round ID by default, so a new round gets a new seed sequence. Set
`ROUND_SEED=42` to use a fixed base seed instead; it is recorded in the summary.

## Naming

All files share the start time of the round in Asia/Ho_Chi_Minh. For a round
started at 14:25 on 9 October 2026:

```text
backtests/645/645_1425_091026/runs/645_1425_091026_1.json
backtests/645/645_1425_091026/runs/645_1425_091026_2.json
...
backtests/645/645_1425_091026/runs/645_1425_091026_10.json
backtests/suggestions/645_1425_091026.json
```

Time is `HHmm`; date is `ddMMyy`. A round can finish in a later minute while
retaining its original timestamp. The same product/minute cannot be reused.
Concurrent runs reserve their product/minute with a temporary lock.

## Per-run evaluation

Each iteration evaluates predict and simulate across four history windows:
30, 60, 120, and all prior draws. The preceding 60 targets form the development
block and the final 60 form the holdout. Same-date draws stay together. The
selected strategy/window maximizes development mean main hits and is frozen
before holdout evaluation.

One seed offset is used per iteration. Offsets are separated by at least
1,000,003, or by more than the sample count when necessary. Each run generates
a new suggestion from its selected configuration using the latest audited
history. Recommendation generation has a separate recorded seed.

## Summary

The final suggestion file is written only after all requested iterations finish. It contains
source filenames, seeds, configurations, holdout metrics, number rankings, and
distinct consensus combinations (`RECOMMENDATIONS=2` by default). Main counts measure appearances in the ten
per-run suggestions. The first combination takes the six highest-ranked main
numbers for 645/655, or five for 535. Further combinations maximize the same summed main-number count while remaining
distinct. A best-first search avoids enumerating the entire ticket space. Ties prefer smaller numbers. Both use the highest-ranked
bonus for 535/655, appended separately.

These maximize the additive main consensus score; they are not estimates of
winning probabilities. Holdout performance is not used to weight the ranking.
All iterations reuse the same historical outcomes. Results remain exploratory.

Raw CSVs are not rewritten. Dataset hashes must stay fixed throughout the round.
If an iteration fails, completed files are kept and no round summary is written.
Use `RESUME=<round_id>` with matching parameters to continue an interrupted round.
New rounds use a new minute. Completed runs are not recomputed. The latest Markdown report is stored in
`docs/EVALUATION.md`.

For a nested 10/30/100-run comparison, use `make stability PRODUCT=645 WORKERS=4`.
See [STABILITY.md](STABILITY.md) for checkpoint metrics and the full directory layout.

Custom stability stages and recommendation counts are supported for all products:

```bash
make stability PRODUCT=655 STAGES="20 50 200" RECOMMENDATIONS=5 WORKERS=4
```
