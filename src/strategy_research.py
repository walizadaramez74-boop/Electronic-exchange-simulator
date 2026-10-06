"""Paired synthetic market-making research using the existing matching engine.

No strategy accesses future fair values. Counterparty flow is correlated with a
hidden future shock to model adverse selection, not to train or validate alpha.
"""
import argparse
import csv
import html
import math
import random
from pathlib import Path
from statistics import mean, pstdev, stdev
from matching_engine import MatchingEngine
from order import Order
from market_making import Account, QuoteConfig, quotes


def make_tape(seed, steps=2000):
    rng=random.Random(seed)
    mid=100.0
    tape=[]
    for i in range(steps):
        shock=rng.gauss(0,.015)
        buy = rng.random() < (.7 if shock>0 else .3)
        tape.append(dict(mid=mid, next_mid=max(1.,mid+shock),
                         side='BUY' if buy else 'SELL', quantity=rng.randint(5,45),
                         limit_offset=rng.uniform(.015,.075),
                         bid_depth=rng.randint(25,200), ask_depth=rng.randint(25,200)))
        mid=tape[-1]['next_mid']
    return tape


def replay(tape, config, max_drawdown=50.0):
    if max_drawdown <= 0 or not math.isfinite(max_drawdown):
        raise ValueError("Positive drawdown limit required")
    halted=False
    engine=MatchingEngine()
    account=Account()
    rows=[]
    next_id=1
    resting=[]
    changes=[]
    peak=0.0
    fills=0
    traded=0
    def submit(side, kind, qty, price, step):
        nonlocal next_id
        order=Order(next_id,side,kind,qty,price,step)
        next_id+=1
        engine.process_order(order)
        return order
    for step,event in enumerate(tape):
        for oid in resting:
            engine.cancel_order(oid)
        resting=[]
        mid=event['mid']
        if step:
            changes.append(mid-tape[step-1]['mid'])
        vol=pstdev(changes[-50:]) if len(changes)>1 else 0.0
        # Replenished background LP quotes: simplified one-level liquidity.
        bid_bg=submit('BUY','LIMIT',event['bid_depth'],mid-.06,step)
        ask_bg=submit('SELL','LIMIT',event['ask_depth'],mid+.06,step)
        resting.extend([bid_bg.order_id,ask_bg.order_id])
        current=account.mark(mid)['net_pnl']
        peak=max(peak,current)
        if peak-current >= max_drawdown:
            halted=True
        bid,ask,bq,aq=quotes(mid,vol,account.inventory,config)
        if halted:
            bq=aq=0
        # Passive quotes only; enforce non-crossing against the background book.
        bid=min(bid,mid+.059)
        ask=max(ask,mid-.059)
        owned={}
        for side,price,qty in [('BUY',bid,bq),('SELL',ask,aq)]:
            if qty:
                order=submit(side,'LIMIT',qty,price,step)
                owned[order.order_id]=side
                resting.append(order.order_id)
        book=engine.order_book
        bd=sum(o.quantity for level in book.bids.values() for o in level)
        ad=sum(o.quantity for level in book.asks.values() for o in level)
        imbalance=(bd-ad)/(bd+ad) if bd+ad else 0.0
        spread=book.best_ask()-book.best_bid()
        before=len(engine.trades)
        sign=1 if event['side']=='BUY' else -1
        limit_price=mid+sign*event.get('limit_offset',.075)
        incoming=submit(event['side'],'LIMIT',event['quantity'],limit_price,step)
        # IOC: any residual counterparty quantity never rests in the book.
        engine.cancel_order(incoming.order_id)
        for trade in engine.trades[before:]:
            oid=trade.buy_order_id if trade.buy_order_id in owned else trade.sell_order_id
            if oid in owned:
                account.fill(owned[oid],trade.quantity,trade.price)
                traded+=trade.quantity
                fills+=1
        if abs(account.inventory)>config.inventory_limit:
            raise AssertionError('Inventory limit breached')
        mark=account.mark(event['next_mid'])
        peak=max(peak,mark['net_pnl'])
        if peak-mark['net_pnl'] >= max_drawdown:
            halted=True
        rows.append(dict(step=step,mid=mid,halted=halted,spread=spread,imbalance=imbalance,
                         rolling_volatility=vol,depth=bd+ad,
                         next_mid_change=event['next_mid']-mid,
                         ioc_unfilled=incoming.quantity,
                         drawdown=peak-mark['net_pnl'],**mark))
    if not rows:
        raise ValueError('Tape must not be empty')
    summary=dict(net_pnl=rows[-1]['net_pnl'], realised_pnl=account.realised,
                 unrealised_pnl=rows[-1]['unrealised_pnl'],fees=account.fees,
                 max_inventory=max(abs(r['inventory']) for r in rows),
                 max_drawdown=max(r['drawdown'] for r in rows),
                 fills=fills, traded_quantity=traded, fill_event_rate=fills/len(rows),
                 halted=halted)
    return rows,summary


def predictive_analysis(rows):
    """Train-only linear OBI fit; chronological holdout against zero-change baseline."""
    split=int(.7*len(rows))
    train,test=rows[:split],rows[split:]
    if len(train)<2 or len(test)<2:
        raise ValueError('Insufficient observations')
    xmean=mean(r['imbalance'] for r in train)
    ymean=mean(r['next_mid_change'] for r in train)
    variance=sum((r['imbalance']-xmean)**2 for r in train)
    slope=sum((r['imbalance']-xmean)*(r['next_mid_change']-ymean) for r in train)/variance if variance else 0.0
    intercept=ymean-slope*xmean
    return dict(train_rows=len(train),test_rows=len(test),slope=slope,intercept=intercept,
        holdout_mse=mean((intercept+slope*r['imbalance']-r['next_mid_change'])**2 for r in test),
        zero_baseline_mse=mean(r['next_mid_change']**2 for r in test))


def write_csv(path, rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def run(output='analysis/strategy', seeds=20, steps=2000):
    if seeds<2 or steps<20:
        raise ValueError('At least two seeds and twenty steps required')
    out=Path(output)
    out.mkdir(parents=True,exist_ok=True)
    summaries=[]
    differences=[]
    for seed in range(seeds):
        tape=make_tape(seed,steps)
        pair={}
        for name,config in [('fixed_spread',QuoteConfig(inventory_skew=0,volatility_multiplier=0)),
                            ('inventory_aware',QuoteConfig())]:
            rows,summary=replay(tape,config)
            summaries.append(dict(seed=seed,strategy=name,**summary))
            pair[name]=summary['net_pnl']
            if seed==0:
                write_csv(out/f'{name}_events.csv',rows)
                if name=='inventory_aware':
                    write_csv(out/'obi_holdout.csv',[predictive_analysis(rows)])
        differences.append(pair['inventory_aware']-pair['fixed_spread'])
    write_csv(out/'strategy_comparison.csv',summaries)
    comparison=dict(seeds=seeds,steps=steps,paired_mean_pnl_difference=mean(differences),
                    standard_error=stdev(differences)/math.sqrt(seeds))
    write_csv(out/'paired_summary.csv',[comparison])
    table='<table><tr>'+''.join('<th>'+k+'</th>' for k in summaries[0])+'</tr>'
    for row in summaries:
        table+='<tr>'+''.join('<td>'+html.escape(f'{v:.4f}' if isinstance(v,float) else str(v))+'</td>' for v in row.values())+'</tr>'
    report='<!doctype html><meta charset="utf-8"><title>Market-Making Research</title><style>body{font:15px system-ui;margin:40px;background:#101a2b;color:#eee}td,th{padding:8px;border-bottom:1px solid #445}table{border-collapse:collapse}h1{color:#68daca}</style><h1>Market-Making Research</h1><p>Synthetic paired replays, seeded order flow, matching-engine fills, fees and hard inventory limits.</p><p>Inventory-aware minus fixed-spread mean net PnL: '+f"{comparison['paired_mean_pnl_difference']:.4f}; standard error: {comparison['standard_error']:.4f}"+'</p><p>No claim of market alpha. Drawdown stop disables new quotes without liquidating inventory. Replenished background liquidity, no latency or historical calibration. Mark-to-market PnL includes residual inventory; there is no terminal liquidation.</p>'+table
    (out/'report.html').write_text(report)
    return comparison

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--output',default='analysis/strategy')
    p.add_argument('--seeds',type=int,default=20)
    p.add_argument('--steps',type=int,default=2000)
    args=p.parse_args()
    print(run(args.output,args.seeds,args.steps))
