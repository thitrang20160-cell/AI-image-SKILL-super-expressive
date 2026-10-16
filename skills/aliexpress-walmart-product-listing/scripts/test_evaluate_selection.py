#!/usr/bin/env python3
"""Synthetic offline checks of margin, missing data, fee tiers and scope."""
import argparse
import copy
import json
from decimal import Decimal
from pathlib import Path
from evaluate_selection import evaluate, fee_for

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--workdir', type=Path, required=True)
    args=parser.parse_args()
    base=args.workdir.resolve()
    base.mkdir(parents=True, exist_ok=True)
    ref=base/'synthetic-evidence.txt'
    ref.write_text('Synthetic fixture, not a real quote or market review.',encoding='utf-8')
    refs=[str(ref)]
    product={'sku':'TEST-001','source':{'selectedVariant':'Blue 1 Pc','evidenceRefs':refs},
             'traffic':{'status':'pass','market':'Walmart US','evidenceRefs':refs},
             'economics':{'costStatus':'verified-repeatable','costs':{'itemUsd':4,'shippingToUsUsd':2,'nonRecoverableTaxUsd':0,'packagingUsd':0,'otherFulfillmentUsd':0,'paymentFxUsd':0,'otherVariableUsd':0},'costEvidenceRefs':refs,'retailPriceUsd':21,'customerShippingUsd':0,'commission':{'scheme':'flat','rate':0.15,'evidenceRefs':refs},'adRate':0.10,'returnLossRate':0.05,'stressCostIncreaseRate':0.20,'assumptionBasis':'Synthetic assumptions'},
             'marketReview':{'status':'pass','platform':'Walmart US','comparableDeliveredPriceCapUsd':24,'evidenceRefs':refs}}
    results=[]
    def check(name,change=None,decision='pass',code=None,thresholds=None):
        value=copy.deepcopy(product)
        if change:change(value)
        result=evaluate(value,base,thresholds)
        assert result['decision']==decision,(name,result)
        if code:assert code in result['pending']+result['rejected'],(name,result)
        results.append({'scenario':name,'passed':True})
        return result
    result=check('complete repeatable model')
    assert result['metrics']['unitContributionUsd']==8.7
    assert result['metrics']['stressUnitContributionUsd']==7.5
    check('unknown shipping stays unknown',lambda p:p['economics']['costs'].update(shippingToUsUsd=None),'hold','cost-incomplete')
    check('first-order price cannot pass repeatable cost',lambda p:p['economics'].update(costStatus='first-order-only'),'hold','repeatable-cost-not-verified')
    check('amazon alone is not walmart demand',lambda p:p['traffic'].update(market='Amazon US'),'hold','target-market-demand-not-reviewed')
    check('amazon alone is not walmart price cap',lambda p:p['marketReview'].update(platform='Amazon US'),'hold','comparable-walmart-price-not-reviewed')
    check('customer-paid freight included in comparison',lambda p:p['economics'].update(customerShippingUsd=5),'reject','customer-price-above-reviewed-comparable-cap')
    check('missing source fact cannot pass',lambda p:p['source'].pop('selectedVariant'),'hold','locked-source-variant-missing')
    check('missing fee rule cannot pass',lambda p:p['economics']['commission'].update(rate=None),'hold','commission-rule-missing')
    check('unreadable source evidence cannot pass',lambda p:p['source'].update(evidenceRefs=['does-not-exist.txt']),'hold','source-evidence-unreadable')
    check('confirmed profit goal changes decision',decision='reject',code='unit-contribution-below-floor',thresholds={'minUnitContributionUsd':9,'minMargin':0})
    def stress_case(p):
        p['economics']['costs'].update(itemUsd=12,shippingToUsUsd=0)
        p['economics'].update(stressCostIncreaseRate=0.5)
    check('positive baseline but loss under cost stress',stress_case,'reject','stress-contribution-negative')
    def loss_case(p):
        p['economics']['costs'].update(itemUsd=50,shippingToUsUsd=0)
        p['economics'].update(retailPriceUsd=65)
        p['marketReview'].update(comparableDeliveredPriceCapUsd=70)
    result=check('15 markup can lose money after variable expenses',loss_case,'reject','unit-contribution-below-floor')
    assert result['metrics']['unitContributionUsd']==-4.5
    for revenue,expected in [('15','0.75'),('15.01','1.50'),('20','2.00'),('20.01','3.00')]:
        assert fee_for(Decimal(revenue),{'scheme':'apparel-us-2026-10-14'})==Decimal(expected)
        results.append({'scenario':'apparel fee boundary '+revenue,'passed':True})
    check('boolean cost is invalid',lambda p:p['economics']['costs'].update(itemUsd=True),'hold','cost-incomplete')
    report={'kind':'synthetic-offline-selection-regression','scenarioCount':len(results),'allPassed':True,'results':results}
    (base/'regression-results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'scenarioCount':len(results),'allPassed':True,'report':str(base/'regression-results.json')}))
if __name__=='__main__':main()
