#!/usr/bin/env python3
"""Offline unit contribution and evidence-gate checks; never publishes or fetches."""
import argparse
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

COST_KEYS = ('itemUsd', 'shippingToUsUsd', 'nonRecoverableTaxUsd', 'packagingUsd',
             'otherFulfillmentUsd', 'paymentFxUsd', 'otherVariableUsd')
CENT = Decimal('0.01')

def number(value, rate=False):
    if value is None or isinstance(value, bool):
        return None
    try:
        result = Decimal(str(value))
        if not result.is_finite() or result < 0 or (rate and result >= 1):
            return None
        return result
    except (InvalidOperation, ValueError):
        return None

def fee_for(revenue, commission):
    scheme = commission.get('scheme')
    if scheme == 'apparel-us-2026-10-14':
        rate = Decimal('0.05') if revenue <= 15 else Decimal('0.10') if revenue <= 20 else Decimal('0.15')
    elif scheme == 'flat':
        rate = number(commission.get('rate'), rate=True)
    else:
        rate = None
    return None if rate is None else (revenue * rate).quantize(CENT, rounding=ROUND_HALF_UP)

def evaluate(product, base, thresholds=None):
    thresholds = thresholds or {}
    pending, rejected = [], []
    def evidence(refs, label):
        if not isinstance(refs, list) or not refs:
            pending.append(label + '-evidence-missing')
            return
        for ref in refs:
            if not isinstance(ref, str) or not ref:
                pending.append(label + '-evidence-unreadable')
                continue
            location = Path(ref)
            if not location.is_absolute():
                location = Path(base) / location
            if not location.is_file():
                pending.append(label + '-evidence-unreadable')
    source = product.get('source') or {}
    if not source.get('selectedVariant'):
        pending.append('locked-source-variant-missing')
    evidence(source.get('evidenceRefs'), 'source')
    traffic = product.get('traffic') or {}
    if traffic.get('status') == 'reject':
        rejected.append('target-market-demand-rejected')
    elif traffic.get('status') != 'pass' or traffic.get('market') != 'Walmart US':
        pending.append('target-market-demand-not-reviewed')
    evidence(traffic.get('evidenceRefs'), 'traffic')
    economics = product.get('economics') or {}
    costs = economics.get('costs') or {}
    amounts = [number(costs.get(key)) for key in COST_KEYS]
    if any(value is None for value in amounts):
        pending.append('cost-incomplete')
    if economics.get('costStatus') != 'verified-repeatable':
        pending.append('repeatable-cost-not-verified')
    evidence(economics.get('costEvidenceRefs'), 'cost')
    price = number(economics.get('retailPriceUsd'))
    shipping = number(economics.get('customerShippingUsd'))
    ad = number(economics.get('adRate'), rate=True)
    loss = number(economics.get('returnLossRate'), rate=True)
    stress = number(economics.get('stressCostIncreaseRate'))
    if price is None or price <= 0 or shipping is None:
        pending.append('price-or-customer-freight-missing')
    if ad is None or loss is None or stress is None or not economics.get('assumptionBasis'):
        pending.append('variable-cost-assumptions-missing')
    commission = economics.get('commission') or {}
    evidence(commission.get('evidenceRefs'), 'commission')
    market = product.get('marketReview') or {}
    cap = number(market.get('comparableDeliveredPriceCapUsd'))
    if market.get('status') == 'reject':
        rejected.append('competition-rejected')
    elif market.get('status') != 'pass' or market.get('platform') != 'Walmart US' or cap is None:
        pending.append('comparable-walmart-price-not-reviewed')
    evidence(market.get('evidenceRefs'), 'market')
    metrics = None
    if price is not None and price > 0 and shipping is not None:
        revenue = price + shipping
        fee = fee_for(revenue, commission)
        if fee is None:
            pending.append('commission-rule-missing')
        if cap is not None and revenue > cap:
            rejected.append('customer-price-above-reviewed-comparable-cap')
        if fee is not None and all(value is not None for value in amounts) and ad is not None and loss is not None and stress is not None:
            cost = sum(amounts)
            profit = revenue - fee - cost - revenue * (ad + loss)
            stress_profit = profit - cost * stress
            margin = profit / revenue
            minimum = number(thresholds.get('minUnitContributionUsd', 0))
            min_margin = number(thresholds.get('minMargin', 0), rate=True)
            if minimum is None or min_margin is None:
                pending.append('invalid-profit-thresholds')
            else:
                if profit <= 0 or profit < minimum:
                    rejected.append('unit-contribution-below-floor')
                if margin < min_margin:
                    rejected.append('margin-below-floor')
            if stress_profit < 0:
                rejected.append('stress-contribution-negative')
            money = lambda value: float(value.quantize(CENT, rounding=ROUND_HALF_UP))
            metrics = {'revenueUsd': money(revenue), 'variableCostUsd': money(cost),
                       'commissionUsd': money(fee), 'adCostUsd': money(revenue * ad),
                       'returnLossReserveUsd': money(revenue * loss),
                       'unitContributionUsd': money(profit), 'margin': float(margin),
                       'stressUnitContributionUsd': money(stress_profit),
                       'basis': 'verified-cost-model' if economics.get('costStatus') == 'verified-repeatable' else 'unverified-cost-scenario'}
    # Missing facts never become a pass even if the arithmetic looks attractive.
    decision = 'reject' if rejected else 'hold' if pending else 'pass'
    return {'sku': product.get('sku'), 'decision': decision, 'pending': list(dict.fromkeys(pending)),
            'rejected': list(dict.fromkeys(rejected)), 'metrics': metrics,
            'limits': 'Checks records and arithmetic; evidence truth, demand and comparability require actual review. Fixed overhead and income tax excluded.'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    batch = json.loads(args.input.read_text(encoding='utf-8-sig'))
    products = batch.get('products') or []
    skus = [product.get('sku') for product in products]
    if not products or not all(skus) or len(skus) != len(set(skus)):
        parser.error('Products need unique nonempty SKUs')
    results = [evaluate(product, args.input.parent, batch.get('thresholds')) for product in products]
    report = {'kind': 'selection-profit-review', 'ok': all(r['decision'] == 'pass' for r in results),
              'skuCount': len(results), 'results': results}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'ok': report['ok'], 'skuCount': len(results), 'decisions': {k: sum(r['decision'] == k for r in results) for k in ('pass', 'reject', 'hold')}, 'report': str(args.report) if args.report else None}))
    raise SystemExit(0 if report['ok'] else 2)

if __name__ == '__main__':
    main()
