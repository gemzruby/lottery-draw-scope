"""Audit datasets and compare strategies on chronological development/test targets."""
import argparse
import hashlib
import json
from concurrent.futures import ProcessPoolExecutor
from datetime import date
from pathlib import Path
from statistics import mean

from main import PRODUCTS, backtest, load

LAUNCH_SOURCE = 'https://vietlott.vn/vi/tin-tuc/tin-trung-thuong/8862-khach-hang-long-an-linh-thuong-hon-15-ty-dong/'


def audit(draws, product):
    warnings, excluded = [], []
    weekdays = {'645': {2,4,6}, '655': {1,3,5}}
    for draw in draws:
        day = date.fromisoformat(draw.date)
        if product == '655' and day < date(2017,8,1):
            excluded.append(draw.code)
            warnings.append({'code': draw.code, 'date': draw.date, 'reason': 'before_655_launch', 'source': LAUNCH_SOURCE})
        elif product in weekdays and day.weekday() not in weekdays[product]:
            warnings.append({'code': draw.code, 'date': draw.date, 'reason': 'unusual_weekday_requires_review'})
        if PRODUCTS[product][2] and draw.bonus is None:
            warnings.append({'code': draw.code, 'date': draw.date, 'reason': 'missing_bonus'})
    return {'records': len(draws), 'warnings': warnings, 'excluded_codes': excluded,
            'independently_verified_results': False}


def summarize(runs, product):
    rows = [row for run in runs for row in run['rows']]
    seed_means = [mean(row['hits'] for row in run['rows']) for run in runs]
    baseline_means = [mean(row['baseline_hits'] for row in run['rows']) for run in runs]
    maximum,k,_ = PRODUCTS[product]
    bonuses = [r for r in rows if r['bonus_hit'] is not None]
    return {'targets_per_seed': len(runs[0]['rows']), 'seed_runs': len(runs),
            'mean_main_hits': mean(seed_means), 'mean_baseline_hits': mean(baseline_means),
            'mean_difference': mean(seed_means)-mean(baseline_means),
            'seed_mean_min': min(seed_means), 'seed_mean_max': max(seed_means),
            'uniform_expected_main_hits': k*k/maximum,
            'at_least_3_main_rate': sum(r['hits']>=3 for r in rows)/len(rows),
            'bonus_match_rate': mean(r['bonus_hit'] for r in bonuses) if bonuses else None,
            'baseline_bonus_match_rate': mean(r['baseline_bonus_hit'] for r in bonuses) if bonuses else None,
            'seed_means': seed_means, 'baseline_seed_means': baseline_means}


def evaluate_product(task, output_path=None):
    product,directory,output,windows,seeds,dev_count,test_count,screen_samples,confirm_samples = task
    source = directory / f'{product}.csv'
    draws = load(str(source),product)
    quality = audit(draws,product)
    excluded = set(quality['excluded_codes'])
    ordered = sorted((d for d in draws if d.code not in excluded),key=lambda d:d.code)
    minimum = max(1,max(windows))
    if len(ordered) < minimum + dev_count + test_count:
        raise ValueError(f'{product}: not enough history for requested split')
    development = ordered[-test_count-dev_count:-test_count]
    holdout = ordered[-test_count:]
    # Split at a date boundary, so both 535 draws on a date stay in the same group.
    while development and development[-1].date == holdout[0].date:
        holdout.insert(0,development.pop())
    if not development:
        raise ValueError('empty development split')
    records = []
    for strategy in ['predict','simulate']:
        for window in windows:
            runs = [backtest(ordered,product,window,minimum,strategy,screen_samples,seed,
                             [d.code for d in development]) for seed in seeds]
            records.append({'strategy':strategy,'window':window,'samples':screen_samples if strategy=='simulate' else None,
                            'summary':summarize(runs,product),'runs':runs})
            print(f'{product}: development {strategy} window={window} done',flush=True)
    selected = max(records,key=lambda r:r['summary']['mean_main_hits'])
    # Freeze strategy and window before computing any holdout scores.
    chosen = {'strategy':selected['strategy'],'window':selected['window']}
    holdout_runs = [backtest(ordered,product,chosen['window'],minimum,chosen['strategy'],confirm_samples,seed,
                             [d.code for d in holdout]) for seed in seeds]
    result = {'product':product,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
              'audit':quality,'protocol': {'windows':windows,'seed_offsets':seeds,'min_history':minimum,
              'screen_samples':screen_samples,'confirmation_samples':confirm_samples,
              'development_codes':[d.code for d in development],'holdout_codes':[d.code for d in holdout],
              'selection_metric':'development mean main hits across seed offsets',
              'holdout_history':'earlier holdout draws become available to later predictions',
              'caveat':'Exploratory: earlier full-history backtests were already inspected. This is not a pristine unseen holdout.'},
              'development':records,'selected':chosen,'holdout':{'summary':summarize(holdout_runs,product),'runs':holdout_runs}}
    output.mkdir(parents=True,exist_ok=True)
    path = Path(output_path) if output_path is not None else output / f'{product}_evaluation.json'
    path.write_text(json.dumps(result,indent=2)+'\n')
    print(f'{product}: saved {path}',flush=True)
    return result


def write_report(results, output):
    lines=['# Strategy evaluation','',
           'Exploratory chronological evaluation. Previous full-history results were already inspected;',
           'the final block is a supplementary holdout, not entirely unseen data.', '',
           'Raw CSV files were preserved. Pre-launch Power 6/55 records were excluded from both history and targets.', '',
           '| Product | Selected strategy | Window | Test draws | Main hits | Baseline | Difference |',
           '| --- | --- | --- | --- | --- | --- | --- |']
    for result in results:
        s=result['holdout']['summary']; chosen=result['selected']
        lines.append(f"| {result['product']} | {chosen['strategy']} | {chosen['window']} | {s['targets_per_seed']} | {s['mean_main_hits']:.3f} | {s['mean_baseline_hits']:.3f} | {s['mean_difference']:+.3f} |")
    lines += ['', 'Seed ranges measure sensitivity to the RNG seed, not confidence intervals.',
           'Overlapping history and repeated seeds do not create independent lottery outcomes.',
           'Nearby seed offsets also overlap the consecutive seeds used inside simulation;',
           'use widely spaced --seeds values for a stronger seed-sensitivity check.',
              'No statistical significance or profit claim is made. Bonus matches are descriptive;',
              'they do not implement prize eligibility. Simulation sample counts may differ between screening',
              'and confirmation; see each JSON protocol. Rankings are selected only on development targets.', '',
              '## Data audit', '']
    for result in results:
        lines.append(f"- {result['product']}: {result['audit']['records']} records; {len(result['audit']['warnings'])} warnings; excluded codes {result['audit']['excluded_codes']}.")
    if all('seed_sensitivity' in r for r in results):
        lines += ['', '## Widely spaced seed check', '',
                  'The selected configuration remains frozen; this is a sensitivity check, not further tuning.', '',
                  '| Product | Mean main hits | Baseline | Difference | Seed mean range |',
                  '| --- | --- | --- | --- | --- |']
        for result in results:
            s=result['seed_sensitivity']['summary']
            lines.append(f"| {result['product']} | {s['mean_main_hits']:.3f} | {s['mean_baseline_hits']:.3f} | {s['mean_difference']:+.3f} | {s['seed_mean_min']:.3f}..{s['seed_mean_max']:.3f} |")
    lines += ['', f'[Official Power 6/55 launch date source]({LAUNCH_SOURCE}).', '',
              'Full audit details, development comparisons, per-seed metrics, and per-draw results are in the JSON files.',
              'The audit checks schema, ranges, unique codes, date parsing, missing bonuses, and unusual weekdays.',
              'It does not independently verify every winning result or guarantee complete history.', '']
    (output/'EVALUATION.md').write_text('\n'.join(lines))


def check_seed_sensitivity(task):
    """Check a frozen configuration with disjoint simulation seed ranges."""
    product,directory,output,offsets = task
    path=output/f'{product}_evaluation.json'
    result=json.loads(path.read_text())
    source=directory/f'{product}.csv'
    if hashlib.sha256(source.read_bytes()).hexdigest()!=result['source_sha256']:
        raise ValueError('Dataset changed since configuration selection')
    draws=[d for d in load(str(source),product) if d.code not in result['audit']['excluded_codes']]
    chosen=result['selected']; protocol=result['protocol']
    runs=[backtest(draws,product,chosen['window'],protocol['min_history'],chosen['strategy'],
                   protocol['confirmation_samples'],seed,protocol['holdout_codes']) for seed in offsets]
    result['seed_sensitivity']={'offsets':offsets,'summary':summarize(runs,product),'runs':runs,
                                'selection_changed':False}
    path.write_text(json.dumps(result,indent=2)+'\n')
    print(f'{product}: widely spaced seed check done',flush=True)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--products',nargs='+',choices=PRODUCTS,default=list(PRODUCTS))
    parser.add_argument('--windows',nargs='+',type=int,default=[30,60,120,0])
    parser.add_argument('--seeds',nargs='+',type=int,default=[0,42,123])
    parser.add_argument('--development-draws',type=int,default=60)
    parser.add_argument('--holdout-draws',type=int,default=60)
    parser.add_argument('--screen-samples',type=int,default=1000)
    parser.add_argument('--confirm-samples',type=int,default=1000)
    parser.add_argument('--data-dir',type=Path,default=Path('databases'))
    parser.add_argument('--output-dir',type=Path,default=Path('backtests/evaluation'))
    parser.add_argument('--sensitivity-only',action='store_true',help='recheck saved configurations with widely spaced seeds')
    args=parser.parse_args()
    if min(args.windows)<0 or min(args.development_draws,args.holdout_draws,args.screen_samples,args.confirm_samples)<1:
        parser.error('windows must be nonnegative; counts must be positive')
    tasks=[(p,args.data_dir,args.output_dir,list(dict.fromkeys(args.windows)),list(dict.fromkeys(args.seeds)),
            args.development_draws,args.holdout_draws,args.screen_samples,args.confirm_samples) for p in dict.fromkeys(args.products)]
    with ProcessPoolExecutor(max_workers=min(3,len(tasks))) as pool:
        if not args.sensitivity_only:
            results=list(pool.map(evaluate_product,tasks))
        spacing=max(args.confirm_samples, args.screen_samples)+1000003
        checks=[(task[0],args.data_dir,args.output_dir,[0,spacing,2*spacing]) for task in tasks]
        results=list(pool.map(check_seed_sensitivity,checks))
    # Keep all project Markdown documentation under docs.
    write_report(results,Path('docs'))


if __name__=='__main__':
    main()
