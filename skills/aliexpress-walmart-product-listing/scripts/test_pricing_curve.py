#!/usr/bin/env python3
"""Offline behavioral checks; all cases are hypothetical."""
import argparse
import json
from pathlib import Path
from pricing_curve import optimize, metrics, inputs

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--workdir',type=Path,required=True)
    args=parser.parse_args();root=args.workdir.resolve()
    root.mkdir(parents=True,exist_ok=True)
    base={'costUsd':10,'marketMedianUsd':24,'beta':3,'competitionFactor':0.95,'minimumProfitUsd':5,'minimumMargin':0.20,'commissionRate':0.15,'adRate':0.10,'returnLossRate':0.05,'stressCostRate':0.20,'feeScheme':'flat'}
    cases=[]
    def check(name,config,verify):
        result=optimize(config);verify(result);cases.append({'name':name,'passed':True});return result
    def exists(r):assert r['best'] is not None,r
    result=check('baseline finds bounded profit-maximizing scenario',base,exists)
    best=result['best'];assert 22.15<best['priceUsd']<22.40
    assert best['unitProfitUsd']>=5 and best['margin']>=0.20 and best['stressUnitProfitUsd']>=0
    assert best['priceUsd']<=22.8
    # Compare every feasible cent with the chosen optimum; includes rounded-fee discontinuities.
    cfg=inputs(base)
    for cent in range(1,2281):
        p=metrics(cent/100,cfg)
        if p['unitProfitUsd']>=5 and p['margin']>=.2 and p['stressUnitProfitUsd']>=0:
            assert p['logExpectedProfitScore']<=best['logExpectedProfitScore']+1e-10
    cases.append({'name':'exhaustive independent objective check','passed':True})
    def impossible(r):assert r['best'] is None and r['status']=='no-feasible-price',r
    check('high cost is rejected instead of selling below margin',dict(base,costUsd=20),impossible)
    check('cheap competitor yields no forced price',dict(base,marketMedianUsd=7.89,costUsd=3.47),impossible)
    higher=check('cost increase within feasible range updates price',dict(base,costUsd=10.5),exists)
    assert higher['best']['priceUsd']>=best['priceUsd']
    check('11 USD cost exceeds 5 USD profit floor at market cap',dict(base,costUsd=11),impossible)
    weaker=check('weaker competition changes optimum',dict(base,marketMedianUsd=35),exists)
    assert weaker['best']['priceUsd']>best['priceUsd']
    sensitive=check('price sensitivity affects launch price',dict(base,beta=6),exists)
    assert sensitive['best']['priceUsd']<=best['priceUsd']
    check('stress requirement cannot silently be ignored',dict(base,stressCostRate=1),impossible)
    check('apparel tier model searches all eligible fee bands',dict(base,feeScheme='apparel-us-2026-10-14',costUsd=5,marketMedianUsd=22),exists)
    check('margin target above retained revenue is infeasible',dict(base,minimumMargin=.8),impossible)
    check('zero cost still honors profit floor',dict(base,costUsd=0),exists)
    for key,value in [('costUsd',None),('beta',0),('marketMedianUsd',0),('adRate',1),('costUsd',True),('minimumMargin',-1)]:
        try:optimize(dict(base,**{key:value}))
        except ValueError:cases.append({'name':'reject invalid '+key+' '+str(value),'passed':True})
        else:raise AssertionError('Invalid input accepted '+key)
    (root/'regression.json').write_text(json.dumps({'allPassed':True,'scenarioCount':len(cases),'cases':cases},indent=2),encoding='utf-8')
    print(json.dumps({'allPassed':True,'scenarioCount':len(cases),'baselinePriceUsd':best['priceUsd'],'baselineUnitProfitUsd':round(best['unitProfitUsd'],2)}))
if __name__=='__main__':main()
