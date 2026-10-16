#!/usr/bin/env python3
"""Synthetic offline regression; no accounts, APIs, publishing or paid generation."""
import argparse
import copy
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from audit_batch import audit_batch, DEFAULTS, ROOT

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workdir',type=Path,required=True)
    args=parser.parse_args();workdir=args.workdir.resolve()
    workdir.mkdir(parents=True,exist_ok=True)
    base=Path(tempfile.mkdtemp(prefix='batch-run-',dir=workdir))
    evidence=base/'synthetic-evidence.txt';evidence.write_text('Synthetic test evidence, not a real source or review.',encoding='utf-8')
    file=base/'synthetic-image.bin';file.write_bytes(b'Synthetic fixture bytes, not a deliverable image.')
    sha=hashlib.sha256(file.read_bytes()).hexdigest()
    listing={'title':'Synthetic blue tape','features':['Synthetic feature'],'description':'Synthetic fixture description.','attributes':{'color':'Blue','packCount':1},'claimReview':{'status':'pass','evidenceRef':str(evidence)}}
    batch={'batchId':'synthetic','destinationCountry':'US','currency':'USD','scopeSkus':['TEST-001'],'storeId':'synthetic-store','inventoryTarget':0,'shipNode':'synthetic-node','preserveCopy':True,'allowedImageHosts':['images.example.com'],'authorization':{'push':True,'storeId':'synthetic-store','estimateMeasurements':True},'products':[{
        'sku':'TEST-001','storeId':'synthetic-store','source':{'url':'https://www.aliexpress.com/item/1234567890.html','selectedVariant':'Blue 1 Pc','observedAt':'2026-10-13T00:00:00Z','evidenceRefs':[str(evidence)],'lockedAttributes':{'color':'Blue','packCount':1}},
        'procurement':{'itemPriceUsd':0.99,'shippingUsd':0,'freeShipping':True,'promotion':{'active':True,'eligibility':'Synthetic new-account condition','limit':'One'}},
        'listing':listing,'originalCopy':{k:copy.deepcopy(listing[k]) for k in ('title','features','description')},'brand':'Synthetic brand','brandAuthorizationEvidenceRef':str(evidence),'retailPriceUsd':3.99,'inventory':0,
        'measurements':[{'field':'packagedWeightG','value':40,'status':'estimated','evidenceRef':str(evidence)}],
        'images':[{'role':r,'file':str(file),'sha256':sha,'hostedSha256':sha,'httpStatus':200,'url':'https://images.example.com/'+r+'.png','visualReview':{'status':'pass','method':'synthetic-fixture','evidenceRef':str(evidence)},'watermark':{'sha256':sha,'synthid':'not_run'}} for r in DEFAULTS['imageRoles']],
        'schemaValidation':{'pass':True,'version':'synthetic-version','evidenceRef':str(evidence)},'identifiers':{'productId':'CUSTOM','productIdType':'GTIN','exemptionRequestAuthorized':True},
        'official':{'itemStatus':'SUCCESS','catalogFound':True,'retailPriceUsd':3.99,'inventory':{'quantity':0,'shipNode':'synthetic-node'},'evidenceRef':str(evidence)}
    }]}
    results=[]
    def check(name,mutate=None,phase='stage',code=None):
        value=copy.deepcopy(batch)
        if mutate:mutate(value,value['products'][0])
        result=audit_batch(value,base,phase)
        if code:assert not result['ok'] and any(e['code']==code for e in result['errors']),(name,result)
        else:assert result['ok'],(name,result)
        results.append({'scenario':name,'passed':True})
    check('valid stage with disclosed estimates')
    check('valid authorized push',phase='push')
    check('valid official acceptance',phase='acceptance')
    check('root aliexpress hostname',lambda b,p:p['source'].update(url='https://aliexpress.com/item/1234567890.html'))
    check('lookalike source hostname',lambda b,p:p['source'].update(url='https://aliexpress.com.example.com/item/1234567890.html'),code='missing-direct-aliexpress-source')
    check('different pack count',lambda b,p:p['listing']['attributes'].update(packCount=200),code='source-attribute-mismatch:packCount')
    check('different color',lambda b,p:p['listing']['attributes'].update(color='Red'),code='source-attribute-mismatch:color')
    check('boolean is not a pack count',lambda b,p:p['listing']['attributes'].update(packCount=True),code='source-attribute-mismatch:packCount')
    check('wrong store',lambda b,p:p.update(storeId='other-store'),code='product-store-mismatch')
    check('extra SKU',lambda b,p:b['products'].append(copy.deepcopy(p)),code='sku-count-or-scope-mismatch')
    check('changed approved copy',lambda b,p:p['listing'].update(title='Changed'),code='locked-copy-changed')
    check('unknown freight',lambda b,p:p['procurement'].update(shippingUsd=None),code='procurement-price-or-promo-conditions')
    check('missing first-order limit',lambda b,p:p['procurement']['promotion'].pop('limit'),code='procurement-price-or-promo-conditions')
    check('3.99 free-shipping promotion boundary',lambda b,p:p['procurement'].update(itemPriceUsd=3.99))
    check('30 free-shipping normal boundary',lambda b,p:p['procurement'].update(itemPriceUsd=30,promotion={'active':False}))
    check('50 delivered normal boundary',lambda b,p:p['procurement'].update(itemPriceUsd=49,shippingUsd=1,freeShipping=False,promotion={'active':False}))
    check('over delivered budget',lambda b,p:p['procurement'].update(itemPriceUsd=49,shippingUsd=2,freeShipping=False,promotion={'active':False}),code='procurement-price-or-promo-conditions')
    check('unverified zero freight is not free shipping',lambda b,p:p['procurement'].update(freeShipping=False),code='procurement-price-or-promo-conditions')
    check('unknown image hash',lambda b,p:p['images'][0].update(sha256='0'*64),code='final-image-hash-mismatch')
    check('hosted old bytes',lambda b,p:p['images'][0].update(hostedSha256='0'*64),code='hosted-bytes-not-verified')
    check('wrong image order',lambda b,p:p['images'].reverse(),code='image-count-or-order')
    check('postprocessing requires fidelity recheck',lambda b,p:p['images'][0].update(postprocessed=True),code='postprocess-fidelity-review')
    check('required detector not run',lambda b,p:b.update(watermarkPolicy={'requiredChannels':['synthid']}),code='required-watermark-check-incomplete:synthid')
    check('explicit remaining-check waiver',lambda b,p:b.update(watermarkPolicy={'requiredChannels':['synthid'],'waivedChannels':['synthid'],'waiverEvidenceRef':str(evidence)}))
    check('known positive not hidden by waiver',lambda b,p:(b.update(watermarkPolicy={'requiredChannels':['synthid'],'waivedChannels':['synthid'],'waiverEvidenceRef':str(evidence)}),p['images'][0]['watermark'].update(synthid='positive')),code='known-positive-watermark')
    check('estimate not authorized',lambda b,p:b['authorization'].update(estimateMeasurements=False),code='estimate-not-authorized')
    check('estimated shipping stock positive',lambda b,p:(b.update(inventoryTarget=1),p.update(inventory=1)),code='estimated-measurement-with-positive-inventory')
    check('staging authorization is not push authorization',lambda b,p:b['authorization'].update(push=False),phase='push',code='push-not-authorized-for-target-store')
    check('schema failure blocks push',lambda b,p:p['schemaValidation'].update(**{'pass':False}),phase='push',code='official-schema-not-passed')
    check('exemption approved and processed is not item success',lambda b,p:p['official'].update(itemStatus='INPROGRESS',feedStatus='PROCESSED',exemptionStatus='APPROVED'),phase='acceptance',code='official-item-not-successful')
    check('official stock mismatch',lambda b,p:p['official']['inventory'].update(quantity=5),phase='acceptance',code='official-inventory-not-verified')
    check('boolean is not official zero stock',lambda b,p:p['official']['inventory'].update(quantity=False),phase='acceptance',code='official-inventory-not-verified')
    check('official price mismatch',lambda b,p:p['official'].update(retailPriceUsd=4.99),phase='acceptance',code='official-price-mismatch')
    check('new selection requires traffic gate',lambda b,p:b.update(selectionGateRequired=True),code='traffic-selection-review')
    def with_selection(b,p):
        b['selectionGateRequired']=True
        p['selectionReview']={'traffic':{'status':'pass','evidenceRef':str(evidence)},'profit':{'status':'pass','evidenceRef':str(evidence),'approvedRetailPriceUsd':p['retailPriceUsd']}}
    check('new selection gates preserve validated authorized push',with_selection,phase='push')
    check('price changed after profit approval',lambda b,p:(with_selection(b,p),p['selectionReview']['profit'].update(approvedRetailPriceUsd=4.99)),code='selection-approved-price-mismatch')
    check('unknown demand is not approved selection',lambda b,p:(with_selection(b,p),p['selectionReview']['traffic'].update(status='unknown')),code='traffic-selection-review')

    # New image workflow: fixtures are isolated and are never real image approvals.
    visual_scripts=ROOT.parent/'safesell-product-visuals'/'scripts'
    if str(visual_scripts) not in sys.path:sys.path.insert(0,str(visual_scripts))
    from test_visual_production_gate import make_fixture, ref, save
    from delivery_gate import evaluate as delivery_evaluate
    from png_provenance_export import export_copy
    from detect_image_signals import summarize
    new_batch=copy.deepcopy(batch);new_batch['visualGateRequired']=True
    fixtures={}
    for im in new_batch['products'][0]['images']:
        role=im['role'];purpose='feature' if role.startswith('feature-') else 'scene' if role.startswith('scene-') else role
        f=make_fixture(base/'visual-fixtures'/role,sku='TEST-001',purpose=purpose,slot_role=role);fixtures[role]=f
        sha=hashlib.sha256(f['output'].read_bytes()).hexdigest()
        im.update(file=str(f['output']),sha256=sha,hostedSha256=sha,watermark={'sha256':sha,'synthid':'not_run'},visualPipeline={'requestRef':ref(f['request_file']),'reviewRef':ref(f['review_file'])})
    def check_visual(name,value=None,code=None,phase='stage'):
        value=copy.deepcopy(new_batch if value is None else value)
        result=audit_batch(value,base,phase)
        if code:assert not result['ok'] and any(e['code']==code for e in result['errors']),(name,result)
        else:assert result['ok'],(name,result)
        results.append({'scenario':name,'passed':True})
    check_visual('new visual contracts pass stage')
    check_visual('new visual contracts pass authorized push',phase='push')
    case=copy.deepcopy(new_batch);case['products'][0]['images'][0].pop('visualPipeline')
    check_visual('new image cannot omit pipeline',case,code='visual-production-gate-not-passed')
    case=copy.deepcopy(new_batch);case['products'][0]['images'][2]['visualPipeline']=copy.deepcopy(case['products'][0]['images'][1]['visualPipeline'])
    check_visual('feature1 record cannot be used for feature2',case,code='visual-production-gate-not-passed')
    f=fixtures['feature-1'];changed=copy.deepcopy(f['review']);changed['checks']['style_match']['status']='unknown'
    changed_file=f['base']/'unknown-style-review.json';save(changed_file,changed)
    case=copy.deepcopy(new_batch);case['products'][0]['images'][1]['visualPipeline']['reviewRef']=ref(changed_file)
    check_visual('current unknown style defeats old pass label',case,code='visual-production-gate-not-passed')
    case=copy.deepcopy(new_batch);case['products'][0]['images'][0]['visualPipeline']['reviewRef']['sha256']='0'*64
    check_visual('stale pipeline wrapper cannot pass',case,code='visual-production-gate-not-passed')
    reused=copy.deepcopy(new_batch)
    old_manifest={'sku':'TEST-001','assets':[{'sku':'TEST-001','role':im['role'],'file':im['file'],'sha256':im['sha256'],'finalApproved':True} for im in reused['products'][0]['images']]}
    old_manifest_file=base/'synthetic-old-manifest.json';save(old_manifest_file,old_manifest)
    for im in reused['products'][0]['images']:
        im.pop('visualPipeline');im.update(reuseExisting=True,reuseManifestRef=ref(old_manifest_file))
    check_visual('unchanged approved existing images can be reused',reused)
    rejected=copy.deepcopy(reused);rejected['rejectedImageSha256s']=[rejected['products'][0]['images'][0]['sha256']]
    check_visual('user rejection overrides historical approval',rejected,code='user-rejected-image-reused')
    unapproved=copy.deepcopy(old_manifest);unapproved['assets'][0]['finalApproved']=False
    unapproved_file=base/'synthetic-unapproved-manifest.json';save(unapproved_file,unapproved)
    case=copy.deepcopy(reused);case['products'][0]['images'][0]['reuseManifestRef']=ref(unapproved_file)
    check_visual('unapproved legacy image cannot be reused',case,code='visual-production-gate-not-passed')

    # Verify that a final-byte bridge is required and actually usable.
    f=fixtures['feature-1'];raw=f['output'].read_bytes();payload=b'synthetic-c2pa\x00fixture'
    import struct,zlib
    tag=b'caBX';chunk=struct.pack('>I',len(payload))+tag+payload+struct.pack('>I',zlib.crc32(tag+payload)&0xffffffff)
    f['output'].write_bytes(raw[:-12]+chunk+raw[-12:])
    f['review']['output']=ref(f['output']);save(f['review_file'],f['review'])
    final=f['base']/'final-export.png';metadata=f['base']/'metadata.json';save(metadata,export_copy(f['output'],final,'remove-c2pa'))
    final_sha=hashlib.sha256(final.read_bytes()).hexdigest()
    rows={name:{'kind':'pixel_watermark','check_status':'not_performed','outcome':'unknown','checked_sha256':final_sha} for name in ('openai_synthid','trustmark_qp')}
    coverage=f['base']/'coverage.json';save(coverage,{'file':str(final),'sha256':final_sha,'detectors':rows,'summary':summarize(rows)})
    delivery=delivery_evaluate(final,f['review_file'],metadata,f['base']/'pixel-not-run.json',accept_pixel_limitations=True,coverage_path=coverage,generation_request=f['request_file'])
    assert delivery['requirements_met'],delivery
    delivered_file=f['base']/'delivery.json';save(delivered_file,delivery)
    bridged=copy.deepcopy(new_batch);im=bridged['products'][0]['images'][1]
    im.update(file=str(final),sha256=final_sha,hostedSha256=final_sha,watermark={'sha256':final_sha,'synthid':'not_run'})
    im['visualPipeline']['reviewRef']=ref(f['review_file'])
    check_visual('changed final bytes require export bridge',bridged,code='visual-production-gate-not-passed')
    im['visualPipeline']['deliveryReportRef']=ref(delivered_file)
    check_visual('bound export bridge permits correct final bytes',bridged)
    report={'kind':'synthetic-offline-regression','scenarioCount':len(results),'allPassed':True,'noNetworkOrBusinessWrites':True,'results':results}
    (base/'synthetic-batch.json').write_text(json.dumps(batch,ensure_ascii=False,indent=2),encoding='utf-8')
    (base/'regression-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'scenarioCount':len(results),'allPassed':True,'report':str(base/'regression-results.json')}))

if __name__=='__main__':main()
