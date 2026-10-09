"""Run seeded strategy evaluations with checkpoints and timestamped summaries."""
import argparse
import hashlib
import json
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo

from evaluate import audit, evaluate_product
from main import MASK64, PRODUCTS, load, predict, simulate

ROOT = Path(__file__).resolve().parent
ROUND_SIZE = 10
TIMEZONE = ZoneInfo('Asia/Ho_Chi_Minh')


def write_json(path, data):
    temporary = path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')
    temporary.replace(path)


def run_once(task):
    product, data_dir, output_dir, round_id, iteration, seed, samples, development, holdout = task[:9]
    round_size=task[9] if len(task)>9 else ROUND_SIZE
    path = output_dir/f'{round_id}_{iteration}.json'
    # One seed per iteration; ten iterations provide ten widely separated offsets.
    result = evaluate_product((product,data_dir,output_dir,[30,60,120,0],[seed],
                               development,holdout,samples,samples), output_path=path)
    source = data_dir/f'{product}.csv'
    if hashlib.sha256(source.read_bytes()).hexdigest()!=result['source_sha256']:
        raise ValueError('Source CSV changed during the round')
    excluded = set(result['audit']['excluded_codes'])
    draws = [d for d in load(str(source),product) if d.code not in excluded]
    window = result['selected']['window']
    history = draws[:window] if window else draws
    generation_seed = (seed + 0x534747455354) & MASK64
    if result['selected']['strategy']=='simulate':
        generation = simulate(history,product,generation_seed,samples)
        numbers = generation['suggested_numbers']
    else:
        generation = predict(history,product,generation_seed)[0]
        numbers = generation['numbers']
    result.update({'round_id':round_id,'iteration':iteration,'round_size':round_size,
                   'suggestion':{'numbers':numbers,'generation_seed':generation_seed,
                                 'history_draws':len(history),'latest_history_date':draws[0].date,
                                 'generation':generation}})
    write_json(path,result)
    print(f'{round_id}: completed {iteration}/{round_size}',flush=True)
    return result


def aggregate(results, round_id, started_at, expected_size=ROUND_SIZE, file_prefix=""):
    if len(results)!=expected_size or {r['iteration'] for r in results}!=set(range(1,expected_size+1)):
        raise ValueError(f'A complete aggregate must contain exactly {expected_size} distinct iterations')
    results = sorted(results,key=lambda r:r['iteration'])
    product = results[0]['product']
    source_hash = results[0]['source_sha256']
    holdout_codes = results[0]['protocol']['holdout_codes']
    if any(r['product']!=product or r['round_id']!=round_id or
           r['source_sha256']!=source_hash or r['protocol']['holdout_codes']!=holdout_codes for r in results):
        raise ValueError('Round results must use the same product, dataset and holdout')
    maximum,k,bonus_max = PRODUCTS[product]
    main_counts,bonus_counts = Counter(),Counter()
    for result in results:
        numbers=result['suggestion']['numbers']
        if len(numbers)!=k+bool(bonus_max) or len(set(numbers[:k]))!=k or any(not 1<=n<=maximum for n in numbers[:k]):
            raise ValueError('Invalid suggested main numbers')
        main_counts.update(numbers[:k])
        if bonus_max:
            if not 1<=numbers[k]<=bonus_max: raise ValueError('Invalid suggested bonus')
            bonus_counts[numbers[k]]+=1
    ranked=sorted(range(1,maximum+1),key=lambda n:(-main_counts[n],n))
    # Two highest-scoring combinations under an additive consensus-count score.
    # The second swaps the lowest-ranked selected main number for the next rank.
    combinations=[ranked[:k],ranked[:k-1]+[ranked[k]]]
    bonus = min(range(1,bonus_max+1),key=lambda n:(-bonus_counts[n],n)) if bonus_max else None
    recommendations=[]
    for rank,chosen in enumerate(combinations,1):
        numbers=sorted(chosen)+([bonus] if bonus is not None else [])
        recommendations.append({'rank':rank,'numbers':numbers,
                                'main_consensus_score':sum(main_counts[n] for n in chosen)})
    return {'round_id':round_id,'product':product,'round_size':expected_size,
            'base_seed':results[0]['protocol']['seed_offsets'][0],
            'started_at':started_at.isoformat(),'completed_at':datetime.now(TIMEZONE).isoformat(),
            'timezone':str(TIMEZONE),'source_sha256':source_hash,
            'latest_history_date':results[0]['suggestion']['latest_history_date'],
            'protocol':results[0]['protocol'],'audit':results[0]['audit'],
            'method':'Count main-number appearances in per-run suggestions; rank by count then number. Return the top two additive-consensus combinations. Bonus uses its most frequent suggestion.',
            'note':'Consensus reflects agreement between seeded runs, not winning probabilities. All runs reuse the same lottery history. Holdout scores are reported but never used to rank suggestions.',
            'recommendations':recommendations,
            'main_ranking':[{'number':n,'round_count':main_counts[n]} for n in ranked],
            'bonus_ranking':[{'number':n,'round_count':bonus_counts[n]} for n in sorted(range(1,bonus_max+1),key=lambda n:(-bonus_counts[n],n))] if bonus_max else [],
            'mean_holdout_main_hits':mean(r['holdout']['summary']['mean_main_hits'] for r in results),
            'mean_holdout_baseline_hits':mean(r['holdout']['summary']['mean_baseline_hits'] for r in results),
            'runs':[{'iteration':r['iteration'],'file':f'{file_prefix}{round_id}_{r["iteration"]}.json',
                     'seed_offset':r['protocol']['seed_offsets'][0],'selected':r['selected'],
                     'suggested_numbers':r['suggestion']['numbers'],
                     'holdout_summary':r['holdout']['summary']} for r in results]}


def run_round(product='645', data_dir=ROOT/'databases', output_dir=ROOT/'backtests',
              seed=None, samples=1000, development=60, holdout=60, workers=2, started_at=None,
              runs=10, checkpoints=None, resume=None):
    if product not in PRODUCTS: raise ValueError('Unknown product')
    if min(samples,development,holdout,workers,runs)<1: raise ValueError('Counts must be positive')
    if workers>4: raise ValueError('workers must be 1..4')
    checkpoints=sorted(set(checkpoints or [runs]))
    if checkpoints[0]<1 or checkpoints[-1]>runs: raise ValueError('Invalid checkpoints')
    if runs not in checkpoints: checkpoints.append(runs)
    output_dir=Path(output_dir);data_dir=Path(data_dir)
    output_dir.mkdir(parents=True,exist_ok=True)
    suggestions=output_dir/'suggestions';suggestions.mkdir(exist_ok=True)
    if resume:
        import re
        if not re.fullmatch(product+r'_\d{4}_\d{6}',resume): raise ValueError('Invalid resume round ID')
        round_id=resume
        round_dir=output_dir/product/round_id
        manifest=json.loads((round_dir/'manifest.json').read_text())
        if manifest.get('origin')=='migrated':
            raise ValueError('Migrated rounds are complete archives; start a new round')
        started_at=datetime.fromisoformat(manifest['started_at'])
        base_seed=manifest['parameters']['base_seed']
        if seed is not None and (seed & MASK64)!=base_seed: raise ValueError('Resume seed mismatch')
    else:
        started_at=(started_at or datetime.now(TIMEZONE)).astimezone(TIMEZONE)
        round_id=f'{product}_{started_at:%H%M_%d%m%y}'
        base_seed=(seed if seed is not None else int(hashlib.sha256(round_id.encode()).hexdigest()[:16],16)) & MASK64
        round_dir=output_dir/product/round_id
        if round_dir.exists() or (suggestions/f'{round_id}.json').exists() or any(output_dir.glob(f'{round_id}_*.json')):
            raise FileExistsError(f'Round {round_id} already exists; use --resume or start in another minute')
        round_dir.mkdir(parents=True,exist_ok=False)
        manifest=None
    lock=round_dir/'.lock'
    with lock.open('x') as f: f.write(str(started_at))
    try:
        source=data_dir/f'{product}.csv'
        source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
        parameters=dict(runs=runs,samples=samples,development=development,holdout=holdout,
                        base_seed=base_seed,checkpoints=checkpoints)
        if manifest is not None:
            if manifest['source_sha256']!=source_hash or manifest['parameters']!=parameters:
                raise ValueError('Resume dataset or parameters differ from saved round')
        else:
            manifest=dict(schema_version=1,round_id=round_id,product=product,started_at=started_at.isoformat(),
                          source_sha256=source_hash,parameters=parameters,completed_iterations=[],
                          status='running',completed_checkpoints=[])
        runs_dir=round_dir/'runs';runs_dir.mkdir(exist_ok=True)
        checkpoint_dir=round_dir/'checkpoints';checkpoint_dir.mkdir(exist_ok=True)
        draws=load(str(source),product)
        quality=audit(draws,product)
        usable=[d for d in draws if d.code not in quality['excluded_codes']]
        if len(usable)<120+development+holdout: raise ValueError('Not enough history for this round')
        stride=max(samples+1,1000003)
        results={}
        for i in range(1,runs+1):
            path=runs_dir/f'{round_id}_{i}.json'
            if path.exists():
                try:
                    result=json.loads(path.read_text())
                except json.JSONDecodeError:
                    if i in manifest.get('completed_iterations',[]): raise
                    continue
                if 'suggestion' not in result and i not in manifest.get('completed_iterations',[]):
                    continue
                if result.get('iteration')!=i or result.get('round_id')!=round_id or result.get('source_sha256')!=source_hash or 'suggestion' not in result:
                    raise ValueError(f'Incomplete or mismatched run: {path}')
                if result['protocol']['seed_offsets']!=[(base_seed+(i-1)*stride)&MASK64]:
                    raise ValueError('Resume run seed mismatch')
                results[i]=result
        prefix=f'{product}/{round_id}/runs/'
        def save_progress():
            if hashlib.sha256(source.read_bytes()).hexdigest()!=source_hash:
                raise ValueError('Source CSV changed during the round')
            manifest['completed_iterations']=sorted(results)
            for size in checkpoints:
                if size not in manifest['completed_checkpoints'] and all(i in results for i in range(1,size+1)):
                    summary=aggregate([results[i] for i in range(1,size+1)],round_id,started_at,size,prefix)
                    write_json(checkpoint_dir/f'{size}.json',summary)
                    if size not in manifest['completed_checkpoints']:
                        manifest['completed_checkpoints'].append(size)
                        print(f'{round_id}: checkpoint {size} saved',flush=True)
            write_json(round_dir/'manifest.json',manifest)
        save_progress()
        tasks=[(product,data_dir,runs_dir,round_id,i,(base_seed+(i-1)*stride)&MASK64,
                samples,development,holdout,runs) for i in range(1,runs+1) if i not in results]
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures=[pool.submit(run_once,task) for task in tasks]
            for future in as_completed(futures):
                result=future.result()
                if result['source_sha256']!=source_hash: raise ValueError('Run dataset hash mismatch')
                results[result['iteration']]=result
                save_progress()
        if hashlib.sha256(source.read_bytes()).hexdigest()!=source_hash:
            raise ValueError('Source CSV changed during the round; no summary written')
        summary=aggregate(list(results.values()),round_id,started_at,runs,prefix)
        write_json(suggestions/f'{round_id}.json',summary)
        manifest['status']='complete';manifest['completed_at']=datetime.now(TIMEZONE).isoformat()
        write_json(round_dir/'manifest.json',manifest)
        print(f'Round complete: {suggestions / (round_id+".json")}',flush=True)
        return summary
    finally:
        lock.unlink(missing_ok=True)


def write_report(summary, directory=ROOT/'docs'):
    lines=['# Latest round evaluation','',f"Round: `{summary['round_id']}` ({summary['timezone']}).",'',
           f"{summary['round_size']} runs evaluated predict and simulate across windows 30, 60, 120, and all history.",
           f"Each run used one different seed offset and {summary['protocol']['confirmation_samples']:,} samples per simulation target.",
           'The strategy and window were selected on development targets before scoring the final holdout.', '',
           '| Run | Strategy | Window | Main hits | Baseline |', '| --- | --- | --- | --- | --- |']
    for row in summary['runs']:
        metric=row['holdout_summary'];chosen=row['selected']
        lines.append(f"| {row['iteration']} | {chosen['strategy']} | {chosen['window']} | {metric['mean_main_hits']:.3f} | {metric['mean_baseline_hits']:.3f} |")
    lines += ['', f"Mean holdout main hits: {summary['mean_holdout_main_hits']:.3f}; baseline: {summary['mean_holdout_baseline_hits']:.3f}.", '',
              '## Consensus suggestions', '']
    for row in summary['recommendations']:
        lines.append(f"- Rank {row['rank']}: {' '.join(f'{n:02d}' for n in row['numbers'])}; main consensus score {row['main_consensus_score']}.")
    lines += ['', 'Consensus counts appearances in the per-run suggestions. Holdout scores do not',
              'weight this ranking. It does not represent winning probabilities or demonstrate',
              'superiority to random selection. All runs reuse the same data; earlier backtests',
              'already inspected this history. This remains exploratory.', '',
              f"[Suggestion JSON](../backtests/suggestions/{summary['round_id']}.json).", '']
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    (directory/'EVALUATION.md').write_text('\n'.join(lines),encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--product',choices=PRODUCTS,default='645')
    parser.add_argument('--seed',type=lambda s:int(s,0),help='optional fixed base seed; otherwise derived from the round ID')
    parser.add_argument('--samples',type=int,default=1000)
    parser.add_argument('--development-draws',type=int,default=60)
    parser.add_argument('--holdout-draws',type=int,default=60)
    parser.add_argument('--workers',type=int,default=2)
    parser.add_argument('--runs',type=int,default=10)
    parser.add_argument('--checkpoints',nargs='+',type=int)
    parser.add_argument('--resume',help='resume an interrupted round ID')
    parser.add_argument('--data-dir',type=Path,default=ROOT/'databases')
    parser.add_argument('--output-dir',type=Path,default=ROOT/'backtests')
    args=parser.parse_args()
    try:
        summary=run_round(args.product,args.data_dir,args.output_dir,args.seed,args.samples,
                          args.development_draws,args.holdout_draws,args.workers,runs=args.runs,
                          checkpoints=args.checkpoints,resume=args.resume)
        if args.output_dir.resolve()==(ROOT/'backtests').resolve():
            write_report(summary)
    except (ValueError,FileExistsError) as error:
        parser.error(str(error))


if __name__=='__main__':
    main()
