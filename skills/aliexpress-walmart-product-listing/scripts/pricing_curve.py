#!/usr/bin/env python3
"""Scenario-only pricing optimizer. No network, live pricing or demand claims."""
import argparse
import json
import math
from pathlib import Path

def finite(value, label, lower=0, upper=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < lower or (upper is not None and value > upper):
        raise ValueError('Invalid '+label)
    return float(value)

def inputs(raw):
    cfg=dict(raw)
    for key in ('costUsd','marketMedianUsd','beta','competitionFactor','minimumProfitUsd','minimumMargin','adRate','returnLossRate','stressCostRate'):
        cfg[key]=finite(cfg.get(key),key)
    if cfg['marketMedianUsd']<=0 or cfg['beta']<=0 or not 0<cfg['competitionFactor']<=1:
        raise ValueError('Market, sensitivity and competition factor must be positive')
    if cfg['adRate']+cfg['returnLossRate']>=1 or cfg['minimumMargin']>=1:
        raise ValueError('Invalid variable rates or margin')
    cfg['feeScheme']=cfg.get('feeScheme','flat')
    if cfg['feeScheme']=='flat':
        cfg['commissionRate']=finite(cfg.get('commissionRate'),'commissionRate',0,0.99)
    elif cfg['feeScheme']!='apparel-us-2026-10-14':
        raise ValueError('Unsupported fee scheme')
    if cfg['marketMedianUsd']*cfg['competitionFactor']>2000:
        raise ValueError('This small-item model supports buyer totals up to 2000 USD')
    return cfg

def commission_rate(price,cfg):
    if cfg['feeScheme']=='apparel-us-2026-10-14':
        return 0.05 if price<=15 else 0.10 if price<=20 else 0.15
    return cfg['commissionRate']

def metrics(price,cfg):
    fee=math.floor(price*commission_rate(price,cfg)*100+0.500000001)/100
    profit=price-fee-cfg['costUsd']-price*(cfg['adRate']+cfg['returnLossRate'])
    stress=profit-cfg['costUsd']*cfg['stressCostRate']
    margin=profit/price
    log_demand=-cfg['beta']*(price/cfg['marketMedianUsd']-1)
    log_score=math.log(profit)+log_demand if profit>0 else -math.inf
    return {'priceUsd':price,'commissionUsd':fee,'unitProfitUsd':profit,'margin':margin,
            'stressUnitProfitUsd':stress,'relativeDemandIndex':100*math.exp(min(700,log_demand)),
            'logExpectedProfitScore':log_score}

def optimize(raw):
    cfg=inputs(raw)
    cap=math.floor(cfg['marketMedianUsd']*cfg['competitionFactor']*100+1e-7)/100
    result={'status':'no-feasible-price','marketCapUsd':cap,'best':None,'firstFeasiblePriceUsd':None,
            'modelStatus':'hypothetical-demand-not-calibrated','parameters':cfg}
    best=None
    for cent in range(1,int(round(cap*100))+1):
        point=metrics(cent/100,cfg)
        if point['unitProfitUsd']<=0 or point['unitProfitUsd']+1e-8<cfg['minimumProfitUsd'] or point['margin']+1e-8<cfg['minimumMargin'] or point['stressUnitProfitUsd']<-1e-8:
            continue
        if result['firstFeasiblePriceUsd'] is None:result['firstFeasiblePriceUsd']=point['priceUsd']
        if best is None or point['logExpectedProfitScore']>best['logExpectedProfitScore']+1e-12:
            best=point
    if best:
        result.update(status='scenario-recommended-price',best=best)
    if cfg['feeScheme']=='flat':
        s=1-cfg['commissionRate']-cfg['adRate']-cfg['returnLossRate']
        floor=None if s<=cfg['minimumMargin'] else max((cfg['costUsd']+cfg['minimumProfitUsd'])/s,cfg['costUsd']/(s-cfg['minimumMargin']),cfg['costUsd']*(1+cfg['stressCostRate'])/s)
        result['continuousApproximation']={'remainingRevenueRate':s,'floorUsd':floor,
            'unconstrainedBestUsd':cfg['costUsd']/s+cfg['marketMedianUsd']/cfg['beta'] if s>0 else None}
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    result=optimize(json.loads(args.input.read_text(encoding='utf-8-sig')))
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps({'status':result['status'],'suggestedBuyerTotalUsd':result['best']['priceUsd'] if result['best'] else None,'report':str(args.report)}))
if __name__=='__main__':main()
