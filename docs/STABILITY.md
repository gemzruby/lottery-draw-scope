# Sampling stability experiments

```bash
make stability PRODUCT=645 SAMPLES=1000 WORKERS=4
```

By default, run 100 evaluations with summaries after iterations 10, 30, and 100. These are
nested prefixes of one seed sequence, so the first ten runs are not recomputed.
See [latest results](STABILITY_RESULTS.md).

For Power 6/55 with five final consensus combinations:

```bash
make stability PRODUCT=655 STAGES="20 50 200" RECOMMENDATIONS=5 SAMPLES=1000 WORKERS=4
```

`STAGES` accepts distinct ascending positive checkpoint sizes; the last size is
the total run count. `RECOMMENDATIONS` controls the number of distinct main
combinations. The highest-ranked bonus is appended separately to each one.
The rank uses summed main-number consensus counts; ties use deterministic rank
indices. It does not enumerate all possible tickets.

Product-specific reports preserve [645 results](STABILITY_645_RESULTS.md) and
655 results when available, while `STABILITY_RESULTS.md` shows the latest run.

## Directory layout

```text
backtests/
  535/<round_id>/
    manifest.json
    runs/
    checkpoints/10.json
  645/<round_id>/
    manifest.json
    runs/<round_id>_1.json ... <round_id>_100.json
    checkpoints/<stage>.json
    comparison.json
  655/<round_id>/
    manifest.json
    runs/
    checkpoints/10.json
  suggestions/
    <round_id>.json
```

Round IDs preserve the product, start time, and date format: `645_HHmm_ddMMyy`.
Existing flat files are moved into product/round/runs without changing their
contents or filenames. Suggestion references are updated to match.

## Metrics

The comparison records the top combinations, selected configuration counts,
mean holdout matches versus baseline, and seed spread. It also measures the
number of main numbers retained between checkpoints and total variation (TV)
of main-number and configuration distributions.

Number distributions divide each count by the run count times the main-number
count. TV is half the summed absolute difference and ranges from 0 to 1.
Smaller TV indicates closer distributions. The boundary margin compares the
last selected and first unselected number's occurrence rates; a tie means zero.

Stable rankings do not establish improved prediction. All runs reuse the same
historical targets. Seed spread is not a confidence interval, and holdout scores
never weight the recommendations. The RNG has a bounded deterministic block
cache to accelerate repeated seeds without changing outputs.

## Resume

```bash
make stability PRODUCT=655 STAGES="20 50 200" RECOMMENDATIONS=5 RESUME=655_HHmm_ddMMyy WORKERS=4
```

Use the actual ID from `manifest.json`. Completed runs are loaded and validated;
only missing runs are computed. Dataset hashes and parameters must match. An
active lock prevents concurrent writers. The final suggestion file is written
only when the entire experiment is complete.
