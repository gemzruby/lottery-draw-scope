#!/usr/bin/env python3
"""Generate weighted lottery tickets, statistics, and historical backtests."""
import argparse, csv, json, sqlite3
from collections import Counter
from itertools import combinations
from dataclasses import dataclass
MASK32=(1<<32)-1; MASK64=(1<<64)-1
PRODUCTS={'535':(35,5,12),'645':(45,6,None),'655':(55,6,55)}
BACKTEST_SEED=0x00c0ffee12345677
BASELINE_SEED=0x175efdd434567869

def rol32(x,n): return ((x<<n)|(x>>(32-n))) & MASK32

class ChaCha8:
    """rand_core seed_from_u64 PCG expansion + 64-bit counter ChaCha8 stream."""
    def __init__(self,seed):
        state=seed & MASK64; self.key=[]
        for _ in range(8):
            state=(state*0x5851f42d4c957f2d+0xa17654e46fbe17f3)&MASK64
            x=((state>>18)^state)>>27; x &= MASK32; r=state>>59
            self.key.append(((x>>r)|(x<<((-r)&31)))&MASK32)
        self.counter=0; self.buf=[]; self.pos=0
    def block(self):
        initial=[0x61707865,0x3320646e,0x79622d32,0x6b206574]+self.key+[self.counter&MASK32,self.counter>>32,0,0]
        x=initial.copy()
        def qr(a,b,c,d):
            x[a]=(x[a]+x[b])&MASK32; x[d]=rol32(x[d]^x[a],16)
            x[c]=(x[c]+x[d])&MASK32; x[b]=rol32(x[b]^x[c],12)
            x[a]=(x[a]+x[b])&MASK32; x[d]=rol32(x[d]^x[a],8)
            x[c]=(x[c]+x[d])&MASK32; x[b]=rol32(x[b]^x[c],7)
        for _ in range(4):
            for indices in [(0,4,8,12),(1,5,9,13),(2,6,10,14),(3,7,11,15),(0,5,10,15),(1,6,11,12),(2,7,8,13),(3,4,9,14)]: qr(*indices)
        self.counter=(self.counter+1)&MASK64
        return [(a+b)&MASK32 for a,b in zip(x,initial)]
    def u32(self):
        if self.pos==len(self.buf):
            self.buf=sum((self.block() for _ in range(4)),[]); self.pos=0
        v=self.buf[self.pos]; self.pos+=1; return v
    def u64(self): return self.u32() | (self.u32()<<32)
    def below64(self,n):
        if not 0<n<=MASK64: raise ValueError('range must be 1..2^64-1')
        zone=((n<<(64-n.bit_length()))-1)&MASK64
        while True:
            m=self.u64()*n
            if (m&MASK64)<=zone: return m>>64
    def below32(self,n):
        zone=(~(((1<<32)-n)%n))&MASK32
        while True:
            m=self.u32()*n
            if (m&MASK32)<=zone: return m>>32

@dataclass(frozen=True)
class Draw:
    code:int
    numbers:tuple
    bonus:int|None=None
    date:str=''

def validate(draws,product):
    maximum,count,bonus_max=PRODUCTS[product]
    codes=set()
    for d in draws:
        if d.code in codes: raise ValueError(f'duplicate draw code {d.code}')
        codes.add(d.code)
        if len(d.numbers)!=count or len(set(d.numbers))!=count or any(not 1<=n<=maximum for n in d.numbers): raise ValueError(f'invalid draw {d.code}')
        if d.bonus is not None and (bonus_max is None or not 1<=d.bonus<=bonus_max): raise ValueError(f'invalid bonus {d.code}')
    return sorted(draws,key=lambda d:d.code,reverse=True)

def load(path,product):
    if path.endswith(('.db','.sqlite','.sqlite3')):
        with sqlite3.connect('file:'+path+'?mode=ro',uri=True) as db:
            rows=db.execute('SELECT draw_code,draw_date,n1,n2,n3,n4,n5,n6,n7,bonus FROM draws WHERE product=? ORDER BY draw_code DESC',(product,)).fetchall()
        k=PRODUCTS[product][1]
        draws=[Draw(int(r[0]),tuple(int(x) for x in r[2:2+k]),int(r[9]) if r[9] is not None and int(r[9])>0 else None,str(r[1])) for r in rows]
    else:
        with open(path,encoding='utf-8-sig',newline='') as f:
            rows=list(csv.DictReader(f))
        draws=[Draw(int(r['draw_code']),tuple(int(x) for x in r['numbers'].replace(',',' ').split()),int(r['bonus']) if r.get('bonus') else None,r.get('draw_date','')) for r in rows]
    return validate(draws,product)

def predict(draws,product,seed,tickets=1,bonus_pool=None):
    """Generate tickets with fixed frequency weights and a reproducible RNG.

    Frequency is fixed across draws/tickets. Repeated main numbers consume RNG
    draws, are discarded, and do not reduce their weight. Sorted main numbers
    plus the appended extra number identify a unique ticket. At most 500 tries.
    """
    maximum,k,bonus_max=PRODUCTS[product]
    if not 0<=tickets<=255: raise ValueError('tickets must be 0..255')
    freq=Counter(n for d in draws for n in d.numbers if 0<=n<=maximum)
    rng=ChaCha8(seed); weights=[freq[n]+1 for n in range(1,maximum+1)]
    pool=list(bonus_pool) if bonus_pool is not None else [d.bonus for d in draws if d.bonus is not None]
    if any(bonus_max is None or not 1<=n<=bonus_max for n in pool): raise ValueError('invalid bonus pool')
    out=[]; seen=set()
    for _ in range(500 if tickets else 0):
        selected=set()
        while len(selected)<k:
            r=rng.below64(sum(weights))
            for n,w in enumerate(weights,1):
                if r<w: selected.add(n); break
                r-=w
        ticket=sorted(selected)
        if bonus_max:
            extra=pool[rng.below64(len(pool))] if pool else rng.below32(bonus_max)+1
            ticket.append(extra)
        key=tuple(ticket)
        if key not in seen:
            seen.add(key); out.append({'numbers':ticket,'label':'heuristic-only'})
            if len(out)>=tickets: break
    return out

def stats(draws,product):
    maximum,_,_=PRODUCTS[product]; freq=Counter(); pairs=Counter(); last={}
    odd=Counter()
    for age,d in enumerate(draws):
        freq.update(d.numbers); pairs.update(combinations(sorted(d.numbers),2)); odd[sum(n%2 for n in d.numbers)]+=1
        for n in d.numbers: last.setdefault(n,age)
    return {'draws':len(draws),'frequency':{n:freq[n] for n in range(1,maximum+1)},'hot':sorted(range(1,maximum+1),key=lambda n:(-freq[n],n))[:10], 'cold':sorted(range(1,maximum+1),key=lambda n:(freq[n],n))[:10], 'gap':{n:last.get(n) for n in range(1,maximum+1)}, 'odd_count_distribution':dict(odd),'pairs':[{'numbers':p,'count':c} for p,c in pairs.most_common(10)]}

def backtest(draws,product,window=60,min_history=1):
    """Historical simulation using only draws preceding each target draw."""
    ordered=sorted(draws,key=lambda d:d.code); rows=[]
    for i,target in enumerate(ordered):
        if i<min_history: continue
        prior=list(reversed(ordered[max(0,i-window):i])) if window else list(reversed(ordered[:i]))
        pred=predict(prior,product,(target.code+BACKTEST_SEED)&MASK64)[0]['numbers']
        base=predict([],product,(target.code+BASELINE_SEED)&MASK64)[0]['numbers']
        k=PRODUCTS[product][1]
        rows.append({'draw_code':target.code,'prediction':pred,'hits':len(set(pred[:k])&set(target.numbers)), 'baseline':base,'baseline_hits':len(set(base[:k])&set(target.numbers))})
    return {'periods':len(rows),'cost_vnd':len(rows)*10000,'hit_histogram':dict(Counter(r['hits'] for r in rows)), 'baseline_hit_histogram':dict(Counter(r['baseline_hits'] for r in rows)), 'rows':rows,'roi':None,'note':'Payout/jackpot rules were not fully recovered; ROI intentionally omitted.'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['predict','stats','backtest']); p.add_argument('--data',required=True)
    p.add_argument('--product',choices=PRODUCTS,default='645'); p.add_argument('--seed',type=lambda s:int(s,0)); p.add_argument('--tickets',type=int,default=1)
    p.add_argument('--window',type=int,default=60,help='0 means all history'); p.add_argument('--target-code',type=int)
    p.add_argument('--min-history',type=int,default=1)
    args=p.parse_args(); draws=load(args.data,args.product)
    if args.window<0: p.error('window must be nonnegative')
    if args.command=='backtest': result=backtest(draws,args.product,args.window,args.min_history)
    else:
        if args.target_code is not None: draws=[d for d in draws if d.code<args.target_code]
        if args.window: draws=draws[:args.window]
        if args.command=='stats': result=stats(draws,args.product)
        else:
            if args.seed is None: p.error('predict requires --seed for reproducible results')
            result={'product':args.product,'seed':args.seed,'history_draws':len(draws),'tickets':predict(draws,args.product,args.seed,args.tickets),'compatibility':'static reconstruction; not compared with original runtime'}
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
