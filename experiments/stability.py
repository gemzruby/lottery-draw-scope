"""Compare configurable nested run prefixes without treating seeds as new draw data."""
import argparse
import json
import re
from collections import Counter
from pathlib import Path
from statistics import pstdev

from run_round import ROOT, run_round, write_json, write_report
from main import PRODUCTS


def organize_legacy(output):
    """Move flat run artifacts into product/round/runs while preserving filenames."""
    output=Path(output)
    pattern=re.compile(r'(535|645|655)_(\d{4})_(\d{6})_(\d+)\.json')
    moved=0
    for path in sorted(output.glob('*.json')):
        match=pattern.fullmatch(path.name)
        if not match: continue
        product,time,day,_=match.groups();round_id=f'{product}_{time}_{day}'
        destination=output/product/round_id/'runs'/path.name
        if destination.exists(): raise FileExistsError(f'Refusing to overwrite {destination}')
        destination.parent.mkdir(parents=True,exist_ok=True)
        path.rename(destination);moved+=1
    for path in sorted((output/'suggestions').glob('*.json')):
        data=json.loads(path.read_text())
        round_id=data['round_id'];product=data['product']
        if not re.fullmatch(product+r'_\d{4}_\d{6}',round_id): raise ValueError('Invalid stored round ID')
        round_dir=output/product/round_id
        for run in data['runs']:
            filename=Path(run['file']).name
            target=round_dir/'runs'/filename
            if not target.exists(): raise FileNotFoundError(target)
            run['file']=target.relative_to(output).as_posix()
        data['layout_version']=2
        write_json(path,data)
        checkpoints=round_dir/'checkpoints';checkpoints.mkdir(exist_ok=True)
        if not (checkpoints/f'{data["round_size"]}.json').exists():
            write_json(checkpoints/f'{data["round_size"]}.json',data)
        manifest=round_dir/'manifest.json'
        if not manifest.exists():
            write_json(manifest,dict(schema_version=1,origin='migrated',round_id=round_id,
                                    product=product,started_at=data['started_at'],status='complete',
                                    source_sha256=data['source_sha256'],
                                    completed_iterations=list(range(1,data['round_size']+1)),
                                    completed_checkpoints=[data['round_size']]))
    return moved


def total_variation(left,right):
    return sum(abs(left.get(key,0)-right.get(key,0)) for key in set(left)|set(right))/2


def compare_checkpoints(summaries):
    if len(summaries)<2: raise ValueError('At least two checkpoints are required')
    summaries=sorted(summaries,key=lambda s:s['round_size'])
    reference=summaries[0]
    rows=[];previous=None
    for summary in summaries:
        if summary['round_id']!=reference['round_id'] or summary['source_sha256']!=reference['source_sha256']:
            raise ValueError('Checkpoints must belong to the same round and dataset')
        size=summary['round_size']
        if previous:
            old=previous['runs']
            if summary['runs'][:len(old)]!=old: raise ValueError('Checkpoints must be nested prefixes')
        k=len(summary['recommendations'][0]['numbers'])-(1 if summary['product']!='645' else 0)
        number_distribution={r['number']:r['round_count']/(size*k) for r in summary['main_ranking']}
        configurations=Counter(f'{r["selected"]["strategy"]}:{r["selected"]["window"]}' for r in summary['runs'])
        configuration_distribution={key:count/size for key,count in configurations.items()}
        hits=[r['holdout_summary']['mean_main_hits'] for r in summary['runs']]
        row={'runs':size,'recommendations':summary['recommendations'],
             'configuration_counts':dict(configurations),'configuration_distribution':configuration_distribution,
             'mean_holdout_main_hits':summary['mean_holdout_main_hits'],
             'mean_holdout_baseline_hits':summary['mean_holdout_baseline_hits'],
             'mean_difference':summary['mean_holdout_main_hits']-summary['mean_holdout_baseline_hits'],
             'seed_mean_standard_deviation':pstdev(hits),
             'top_main_boundary_margin':(summary['main_ranking'][k-1]['round_count']-summary['main_ranking'][k]['round_count'])/size,
             'main_number_distribution':number_distribution}
        if rows:
            prior=rows[-1]
            before=set(prior['recommendations'][0]['numbers'][:k]);after=set(row['recommendations'][0]['numbers'][:k])
            row['change_from_previous']={'previous_runs':prior['runs'],'retained_main_numbers':len(before&after),
                'main_number_jaccard':len(before&after)/len(before|after),
                'main_distribution_total_variation':total_variation(prior['main_number_distribution'],number_distribution),
                'configuration_total_variation':total_variation(prior['configuration_distribution'],configuration_distribution),
                'mean_hit_change':row['mean_holdout_main_hits']-prior['mean_holdout_main_hits']}
        rows.append(row);previous=summary
    return {'round_id':reference['round_id'],'product':reference['product'],
            'source_sha256':reference['source_sha256'],'checkpoints':rows,
            'note':'Nested prefixes reuse the same seed sequence and historical targets. Changes measure sampling stability, not independent predictive evidence. Seed spread is not a confidence interval.'}


def write_stability_report(comparison, path):
    stages=', '.join(str(row['runs']) for row in comparison['checkpoints'])
    lines=['# Sampling stability experiment','',f"Round: `{comparison['round_id']}`.",'',
           f'The {stages}-run checkpoints are nested prefixes of the same round.',
           'All runs use the same development and holdout dates. The data are exploratory,',
           'not an unseen independent test set.', '',
           '| Runs | First combination (bonus last if applicable) | Main hits | Baseline | Difference | Seed SD |',
           '| --- | --- | --- | --- | --- | --- |']
    for row in comparison['checkpoints']:
        nums=' '.join(f'{n:02d}' for n in row['recommendations'][0]['numbers'])
        lines.append(f"| {row['runs']} | {nums} | {row['mean_holdout_main_hits']:.3f} | {row['mean_holdout_baseline_hits']:.3f} | {row['mean_difference']:+.3f} | {row['seed_mean_standard_deviation']:.3f} |")
    lines += ['', '## Changes between checkpoints','',
              '| Change | Main numbers retained | Distribution TV | Configuration TV |',
              '| --- | --- | --- | --- |']
    for row in comparison['checkpoints'][1:]:
        change=row['change_from_previous']
        lines.append(f"| {change['previous_runs']} to {row['runs']} | {change['retained_main_numbers']} | {change['main_distribution_total_variation']:.3f} | {change['configuration_total_variation']:.3f} |")
    lines += ['', '## Final consensus combinations', '',
              '| Rank | Main numbers | Bonus | Consensus score |',
              '| --- | --- | --- | --- |']
    k=PRODUCTS[comparison['product']][1]
    for recommendation in comparison['checkpoints'][-1]['recommendations']:
        numbers=recommendation['numbers']
        main=' '.join(f'{n:02d}' for n in numbers[:k])
        bonus=f'{numbers[k]:02d}' if len(numbers)>k else '-'
        lines.append(f"| {recommendation['rank']} | {main} | {bonus} | {recommendation['main_consensus_score']} |")
    lines += ['', 'Total variation (TV) ranges from 0 to 1; smaller values indicate closer distributions.',
              'Seed SD is descriptive spread across runs, not statistical uncertainty in future draws.',
              'The boundary margin and full configuration counts are in comparison.json.',
              'A stable consensus does not imply improved winning probabilities.', '',
              f"[Comparison JSON](../backtests/{comparison['product']}/{comparison['round_id']}/comparison.json).",'']
    Path(path).write_text('\n'.join(lines),encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--product',choices=['535','645','655'],default='645')
    parser.add_argument('--stages',nargs='+',type=int,default=[10,30,100])
    parser.add_argument('--recommendations',type=int,default=2)
    parser.add_argument('--samples',type=int,default=1000)
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--seed',type=lambda s:int(s,0))
    parser.add_argument('--resume')
    parser.add_argument('--output-dir',type=Path,default=ROOT/'backtests')
    args=parser.parse_args()
    if len(args.stages)<2 or args.stages!=sorted(set(args.stages)) or min(args.stages)<1:
        parser.error('stages must contain at least two distinct positive ascending values')
    organize_legacy(args.output_dir)
    summary=run_round(product=args.product,output_dir=args.output_dir,seed=args.seed,
                      samples=args.samples,workers=args.workers,runs=args.stages[-1],checkpoints=args.stages,
                      resume=args.resume,recommendation_count=args.recommendations)
    directory=args.output_dir/args.product/summary['round_id']
    snapshots=[json.loads((directory/'checkpoints'/f'{n}.json').read_text()) for n in args.stages]
    comparison=compare_checkpoints(snapshots)
    write_json(directory/'comparison.json',comparison)
    write_report(summary)
    write_stability_report(comparison,ROOT/'docs/STABILITY_RESULTS.md')
    write_stability_report(comparison,ROOT/f'docs/STABILITY_{args.product}_RESULTS.md')
    print(f'Stability comparison: {directory / "comparison.json"}',flush=True)


if __name__=='__main__':
    main()
