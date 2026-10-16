#!/usr/bin/env python3
"""Read-only checks for a normalized AliExpress -> Walmart US batch."""
import argparse
import hashlib
import json
import importlib.util
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = json.loads((ROOT/'references/project-profile.json').read_text(encoding='utf-8'))

def visual_pipeline_gate(request, review, sku, role):
    candidates = [ROOT.parent/'safesell-product-visuals']
    scripts = next((p/'scripts' for p in candidates if (p/'scripts/visual_production_gate.py').is_file()), None)
    if scripts is None:
        raise ValueError('visual-production-skill-unavailable')
    if str(scripts) not in sys.path:
        sys.path.insert(0,str(scripts))
    spec = importlib.util.spec_from_file_location('_safesell_visual_production_gate',scripts/'visual_production_gate.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    purpose = 'feature' if role.startswith('feature-') else 'scene' if role.startswith('scene-') else role
    return module.evaluate(request, review, expected_sku=sku, expected_purpose=purpose, expected_role=role)

def money(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        n=Decimal(str(value))
        return n if n.is_finite() and n>=0 else None
    except InvalidOperation:
        return None

def price_bucket(p, policy):
    cost=money(p.get('itemPriceUsd')); freight=money(p.get('shippingUsd'))
    if cost is None or freight is None:
        return None
    free=p.get('freeShipping')
    if not isinstance(free,bool) or (free and freight!=0) or (not free and freight==0):
        return None
    promo=p.get('promotion') or {}
    if promo.get('active') and (not promo.get('eligibility') or not promo.get('limit')):
        return None
    if promo.get('active') and cost==money(policy['preferredPromoItemPriceUsd']):
        return 'preferred-0.99-promo'
    if promo.get('active') and free and money(policy['freeShippingPromoMinUsd'])<=cost<=money(policy['freeShippingPromoMaxUsd']):
        return 'free-shipping-promo'
    if free and money(policy['normalFreeShippingMinUsd'])<=cost<=money(policy['normalFreeShippingMaxUsd']):
        return 'normal-free-shipping'
    if not free and money(policy['normalPaidShippingLandedMinUsd'])<=cost+freight<=money(policy['normalPaidShippingLandedMaxUsd']):
        return 'normal-paid-shipping'
    return None

def audit_batch(batch, base, phase='stage'):
    base=Path(base)
    errors=[]; warnings=[]; observed=[]
    def issue(code,sku='',warning=False):
        (warnings if warning else errors).append({'code':code,'sku':sku})
    def path_for(ref):
        p=Path(ref)
        return p if p.is_absolute() else base/p
    def evidence(ref,code,sku):
        if not isinstance(ref,str) or not ref.strip() or not path_for(ref).is_file():
            issue(code,sku); return False
        return True
    def reviewed(r,code,sku):
        if not isinstance(r,dict) or r.get('status')!='pass':
            issue(code,sku); return
        evidence(r.get('evidenceRef'),code+'-evidence',sku)
    def bound_json(ref):
        if not isinstance(ref,dict):raise ValueError('bound-ref-missing')
        file=path_for(ref['file'])
        if hashlib.sha256(file.read_bytes()).hexdigest()!=ref.get('sha256'):raise ValueError('bound-ref-stale')
        value=json.loads(file.read_text(encoding='utf-8-sig'))
        if not isinstance(value,dict):raise ValueError('bound-ref-not-object')
        return file,value
    if batch.get('destinationCountry')!='US' or batch.get('currency')!='USD':
        issue('unsupported-country-or-currency')
    scope=batch.get('scopeSkus',[]); products=batch.get('products',[])
    if not isinstance(scope,list) or not scope or len(set(scope))!=len(scope):
        issue('invalid-sku-scope')
    if not isinstance(products,list):
        return {'ok':False,'phase':phase,'errors':[{'code':'invalid-products','sku':''}],'warnings':[],'products':[]}
    skus=[p.get('sku') for p in products if isinstance(p,dict)]
    if len(skus)!=len(products) or len(set(skus))!=len(skus) or set(skus)!=set(scope):
        issue('sku-count-or-scope-mismatch')
    store=batch.get('storeId'); target=batch.get('inventoryTarget')
    if not store or isinstance(target,bool) or not isinstance(target,int) or target<0:
        issue('invalid-store-or-inventory-target')
    authorization=batch.get('authorization') or {}
    if phase in ('push','acceptance') and (authorization.get('push') is not True or authorization.get('storeId')!=store):
        issue('push-not-authorized-for-target-store')
    roles=batch.get('imageRoles',DEFAULTS['imageRoles'])
    policy=batch.get('pricePolicy',DEFAULTS['pricePolicy'])
    watermark_policy=batch.get('watermarkPolicy') or {}
    visual_required=batch.get('visualGateRequired',False)
    if type(visual_required) is not bool:issue('invalid-visual-gate-policy')
    if not visual_required:issue('legacy-visual-production-not-enforced',warning=True)
    required=watermark_policy.get('requiredChannels',[])
    waived=watermark_policy.get('waivedChannels',[])
    if waived:
        evidence(watermark_policy.get('waiverEvidenceRef'),'watermark-waiver-evidence','')
    for p in products:
        if not isinstance(p,dict):continue
        sku=p.get('sku',''); src=p.get('source') or {}; listing=p.get('listing') or {}
        if batch.get('selectionGateRequired') is True:
            selection=p.get('selectionReview') or {}
            reviewed(selection.get('traffic'),'traffic-selection-review',sku)
            reviewed(selection.get('profit'),'profit-selection-review',sku)
            approved=money((selection.get('profit') or {}).get('approvedRetailPriceUsd'))
            if approved is None or approved<=0 or approved!=money(p.get('retailPriceUsd')):
                issue('selection-approved-price-mismatch',sku)
        if p.get('storeId')!=store:issue('product-store-mismatch',sku)
        if p.get('inventory')!=target or isinstance(p.get('inventory'),bool):issue('inventory-target-mismatch',sku)
        source_url=urlparse(src.get('url') or '')
        host=source_url.hostname or ''
        if source_url.scheme!='https' or not (host=='aliexpress.com' or host.endswith('.aliexpress.com')) or '/item/' not in source_url.path:
            issue('missing-direct-aliexpress-source',sku)
        if not src.get('selectedVariant') or not src.get('observedAt'):issue('variant-or-observation-missing',sku)
        refs=src.get('evidenceRefs') or []
        if not refs:issue('source-evidence-missing',sku)
        for ref in refs:evidence(ref,'source-evidence-unreadable',sku)
        locked=src.get('lockedAttributes') or {}
        if not locked:issue('locked-source-attributes-missing',sku)
        for key,value in locked.items():
            actual=listing.get('attributes',{}).get(key)
            if actual!=value or isinstance(actual,bool)!=isinstance(value,bool):issue('source-attribute-mismatch:'+key,sku)
        if not listing.get('title') or not listing.get('description') or not isinstance(listing.get('features'),list) or not listing.get('features'):
            issue('listing-copy-incomplete',sku)
        reviewed(listing.get('claimReview'),'copy-claim-review',sku)
        if batch.get('preserveCopy'):
            old=p.get('originalCopy') or {}
            if any(listing.get(key)!=old.get(key) for key in ('title','features','description')):issue('locked-copy-changed',sku)
        bucket=price_bucket(p.get('procurement') or {},policy)
        if not bucket:issue('procurement-price-or-promo-conditions',sku)
        observed.append({'sku':sku,'priceBucket':bucket})
        for measurement in p.get('measurements') or []:
            status=measurement.get('status')
            if status not in ('measured','supplier-stated','estimated'):issue('unknown-measurement-status',sku)
            evidence(measurement.get('evidenceRef'),'measurement-evidence',sku)
            if money(measurement.get('value')) is None:issue('measurement-value-invalid',sku)
            if status=='estimated':
                if authorization.get('estimateMeasurements') is not True:issue('estimate-not-authorized',sku)
                if target!=0:issue('estimated-measurement-with-positive-inventory',sku)
                issue('measurement-estimated-not-measured',sku,warning=True)
        images=p.get('images') or []
        if [im.get('role') for im in images]!=roles:issue('image-count-or-order',sku)
        urls=[im.get('url') for im in images]
        if len(set(urls))!=len(urls):issue('duplicate-image-url',sku)
        for im in images:
            sha=im.get('sha256')
            if sha in batch.get('rejectedImageSha256s',[]):issue('user-rejected-image-reused',sku)
            valid_file=evidence(im.get('file'),'image-file-missing',sku)
            if valid_file and hashlib.sha256(path_for(im['file']).read_bytes()).hexdigest()!=sha:issue('final-image-hash-mismatch',sku)
            if im.get('hostedSha256')!=sha or im.get('httpStatus')!=200:issue('hosted-bytes-not-verified',sku)
            u=urlparse(im.get('url') or '')
            if u.scheme!='https' or not u.hostname or u.username or u.password:issue('invalid-image-url',sku)
            if batch.get('allowedImageHosts') and u.hostname not in batch['allowedImageHosts']:issue('image-host-mismatch',sku)
            reviewed(im.get('visualReview'),'image-visual-review',sku)
            pipeline=im.get('visualPipeline')
            if pipeline or visual_required:
                try:
                    if not pipeline and im.get('reuseExisting') is True:
                        old_file,old=bound_json(im.get('reuseManifestRef'))
                        matches=[a for a in old.get('assets',[]) if a.get('sku',old.get('sku'))==sku and a.get('role')==im.get('role') and a.get('sha256')==sha and a.get('finalApproved') is True]
                        if len(matches)!=1:raise ValueError('reuse-asset-not-approved-or-unrelated')
                        old_image=Path(matches[0]['file'])
                        if not old_image.is_absolute():old_image=old_file.parent/old_image
                        if hashlib.sha256(old_image.read_bytes()).hexdigest()!=sha:raise ValueError('reuse-image-changed')
                        issue('legacy-image-reused-with-bound-approval',sku,warning=True)
                    else:
                        req_file,_=bound_json(pipeline.get('requestRef'))
                        review_file,_=bound_json(pipeline.get('reviewRef'))
                        checked=visual_pipeline_gate(req_file,review_file,sku,im['role'])
                        if not checked['ok']:raise ValueError('live-visual-review-failed')
                        if checked['output']['sha256']!=sha:
                            _,delivered=bound_json(pipeline.get('deliveryReportRef'))
                            linked=delivered.get('visual_production') or {}
                            if delivered.get('requirements_met') is not True or delivered.get('image',{}).get('sha256')!=sha or linked.get('ok') is not True or linked.get('output')!=checked['output']:
                                raise ValueError('final-export-not-linked-to-reviewed-generation')
                            live={r['file']:r['sha256'] for r in checked['evidence']}
                            recorded={r['file']:r['sha256'] for r in linked.get('evidence',[])}
                            if live!=recorded:raise ValueError('delivery-pipeline-inputs-stale')
                except (OSError,ValueError,TypeError,KeyError,AttributeError,ImportError):
                    issue('visual-production-gate-not-passed',sku)
            wm=im.get('watermark') or {}
            reported=[x for x in wm if x!='sha256']
            if (reported or required) and wm.get('sha256')!=sha:issue('watermark-not-bound-to-final-bytes',sku)
            for channel in set(required)|set(reported):
                value=wm.get(channel,'not_run')
                if value not in ('negative','positive','unknown','not_run','error'):issue('invalid-watermark-status',sku)
                if value=='positive':
                    if watermark_policy.get('knownPositiveAccepted') is not True:issue('known-positive-watermark',sku)
                    else:
                        evidence(watermark_policy.get('knownPositiveAcceptanceEvidenceRef'),'known-positive-acceptance-evidence',sku)
                        issue('known-positive-explicitly-accepted',sku,warning=True)
                elif channel in required and value!='negative' and channel not in waived:issue('required-watermark-check-incomplete:'+channel,sku)
                elif value in ('unknown','not_run','error'):issue('watermark-'+value+':'+channel,sku,warning=True)
            if im.get('postprocessed'):reviewed(im.get('postProcessReview'),'postprocess-fidelity-review',sku)
        if phase in ('push','acceptance'):
            if not p.get('brand') or not p.get('brandAuthorizationEvidenceRef'):issue('brand-not-confirmed',sku)
            else:evidence(p['brandAuthorizationEvidenceRef'],'brand-authorization-evidence',sku)
            if money(p.get('retailPriceUsd')) is None or money(p.get('retailPriceUsd'))<=0:issue('retail-price-missing',sku)
            validation=p.get('schemaValidation') or {}
            if validation.get('pass') is not True or not validation.get('version'):issue('official-schema-not-passed',sku)
            evidence(validation.get('evidenceRef'),'schema-validation-evidence',sku)
            identifiers=p.get('identifiers') or {}
            if identifiers.get('productId')=='CUSTOM':
                if identifiers.get('productIdType')!='GTIN' or identifiers.get('exemptionRequestAuthorized') is not True:issue('gtin-exemption-not-authorized',sku)
            elif not identifiers.get('productId') or identifiers.get('verifiedForProduct') is not True:
                issue('real-product-identifier-not-confirmed',sku)
            else:evidence(identifiers.get('evidenceRef'),'product-identifier-evidence',sku)
        if phase=='acceptance':
            official=p.get('official') or {}; inventory=official.get('inventory') or {}
            if official.get('itemStatus')!='SUCCESS' or official.get('catalogFound') is not True:issue('official-item-not-successful',sku)
            if money(official.get('retailPriceUsd'))!=money(p.get('retailPriceUsd')):issue('official-price-mismatch',sku)
            if not batch.get('shipNode') or inventory.get('shipNode')!=batch['shipNode'] or inventory.get('quantity')!=target or isinstance(inventory.get('quantity'),bool):issue('official-inventory-not-verified',sku)
            evidence(official.get('evidenceRef'),'official-receipt-evidence',sku)
    return {'ok':not errors,'phase':phase,'skuCount':len(products),'errors':errors,'warnings':warnings,'products':observed,'limits':'Checks normalized records and local bytes; does not establish source truth, visual fidelity, or official API success independently.'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch',type=Path,required=True)
    parser.add_argument('--phase',choices=('stage','push','acceptance'),default='stage')
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    batch=json.loads(args.batch.read_text(encoding='utf-8-sig'))
    result=audit_batch(batch,args.batch.parent,args.phase)
    output=json.dumps(result,ensure_ascii=False,indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(output,encoding='utf-8')
    print(output)
    raise SystemExit(0 if result['ok'] else 2)

if __name__=='__main__':main()
