"""Validate a real before/process/after chain. Never modifies images or invokes a detector."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode=True
from verify_pixel_watermark import classify,ENDPOINT

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as handle:
        while chunk:=handle.read(4*1024*1024): h.update(chunk)
    return h.hexdigest()

def load(path):
    path=Path(path).resolve()
    value=json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(value,dict): raise ValueError('Expected a report object')
    return value,{'file':str(path),'sha256':sha(path)}

def checked_signal(path,image):
    record,reference=load(path)
    image=Path(image).resolve()
    if Path(record.get('file','')).resolve()!=image or record.get('sha256')!=sha(image):
        raise ValueError('Detector receipt does not bind the current image')
    if record.get('check_status')!='completed': return 'unknown',reference
    if record.get('endpoint')==ENDPOINT:
        outcome=classify(record.get('response'))['outcome']
        if outcome!=record.get('outcome'): raise ValueError('API classification mismatch')
        return outcome,reference
    manual_sources={
        'https://synthid.com/':'google_ui',
        'https://openai.com/verify':'openai_ui',
    }
    if record.get('entrypoint') not in manual_sources or record.get('receipt_type')!='actual_browser_UI_and_screenshot':
        raise ValueError('Unsupported manual detector evidence')
    if record.get('api_response') is not None: raise ValueError('Manual UI receipt cannot impersonate an API response')
    shot=record.get('screenshot',{})
    shot_path=Path(shot.get('file','')).resolve()
    if sha(shot_path)!=shot.get('sha256'): raise ValueError('Manual screenshot changed')
    with shot_path.open('rb') as handle: header=handle.read(8)
    if not (header.startswith(b'\xff\xd8\xff') or header==b'\x89PNG\r\n\x1a\n'):
        raise ValueError('Expected real PNG or JPEG screenshot bytes')
    dom=record.get('dom_snapshot')
    if dom and sha(dom['file'])!=dom.get('sha256'): raise ValueError('DOM evidence changed')
    outcome=record.get('outcome')
    if outcome not in ('detected','not_detected') or not record.get('visible_result'):
        return 'unknown',reference
    if manual_sources[record['entrypoint']]=='openai_ui':
        if not dom or record.get('signal_results',{}).get('synthid')!=outcome:
            raise ValueError('OpenAI UI receipt requires bound details for SynthID')
        observed=Path(dom['file']).read_text(encoding='utf-8-sig')
        markers={'detected':('- generic: 检测到 SynthID','- generic: SynthID detected'),
                 'not_detected':('- generic: 未检测到 SynthID','- generic: SynthID not detected')}
        if not any(marker in observed for marker in markers[outcome]):
            raise ValueError('OpenAI detail observation does not match SynthID outcome')
    return outcome,reference

def decide(before,after,changed,quality):
    if before!='detected': return 'baseline_unconfirmed'
    if not changed: return 'no_pixel_processing'
    if after=='detected': return 'still_detected'
    if after!='not_detected': return 'verification_unknown'
    if quality=='fail': return 'rejected_quality'
    if quality!='pass': return 'postprocess_quality_pending'
    return 'supported_signal_cleared_on_this_file'

def evaluate(source,output,before_path,process_path,after_path,quality_path=None):
    from PIL import Image,ImageChops
    source=Path(source).resolve(); output=Path(output).resolve()
    before,before_ref=checked_signal(before_path,source)
    after,after_ref=checked_signal(after_path,output)
    process,process_ref=load(process_path)
    if process.get('kind')!='pixel_processing_execution' or process.get('status')!='completed':
        raise ValueError('Actual completed pixel-processing receipt required')
    for name,path in [('input',source),('output',output)]:
        ref=process.get(name,{})
        original=Path(ref.get('file','')).resolve()
        if (ref.get('sha256')!=sha(path) or sha(original)!=ref.get('sha256')
                or (name=='input' and original!=path)):
            raise ValueError('Processing chain does not bind the actual files')
    if process.get('original_unchanged') is not True: raise ValueError('Original integrity not recorded')
    with Image.open(source) as a,Image.open(output) as b:
        if a.size!=b.size or a.mode!=b.mode: raise ValueError('Processing changed size or mode')
        changed=ImageChops.difference(a,b).getbbox() is not None
    if changed!=process.get('pixels_changed'): raise ValueError('Pixel-change claim mismatch')
    quality='unknown'; quality_ref=None
    if quality_path:
        review,quality_ref=load(quality_path)
        if review.get('kind')!='postprocess-preservation-review': raise ValueError('Wrong review scope')
        if review.get('source',{}).get('sha256')!=sha(source) or review.get('output',{}).get('sha256')!=sha(output):
            raise ValueError('Preservation review is stale')
        required=('composition','product_structure','quantity_and_variant','exact_copy','texture_and_color','contact_and_hands')
        checks=review.get('checks',{})
        statuses=[checks.get(name,{}).get('status','unknown') for name in required]
        if 'fail' in statuses: quality='fail'
        elif all(s=='pass' for s in statuses[:5]) and statuses[5] in ('pass','not-applicable'):
            quality='pass'
    state=decide(before,after,changed,quality)
    transition=before=='detected' and after=='not_detected' and changed
    return {'schema_version':1,'checked_at':datetime.now(timezone.utc).isoformat(),
        'source':{'file':str(source),'sha256':sha(source)},'output':{'file':str(output),'sha256':sha(output)},
        'signal':'SynthID supported by the recorded official detector',
        'before':before,'after':after,'pixels_changed':changed,'preservation_review':quality,
        'state':state,'verified_signal_transition':transition,
        'removal_verified_for_this_file':state=='supported_signal_cleared_on_this_file',
        'eligible_for_final_listing_delivery':False,'delivery_status':'working',
        'evidence':{'before':before_ref,'processing':process_ref,'after':after_ref,'quality':quality_ref},
        'limits':['No universal watermark-absence, human-authorship or marketplace-acceptance claim.',
            'This validates recorded file consistency, not the truth of operator observations.',
            'Postprocess preservation is separate from original SKU fidelity, expanded coverage and the final delivery gate.',
            'One verified file does not approve an entire model, batch or parameter set.']}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('source','output','before','processing','after','report'): p.add_argument('--'+arg,required=True)
    p.add_argument('--quality-review')
    a=p.parse_args(); path=Path(a.report).resolve()
    protected=[Path(x).resolve() for x in (a.source,a.output,a.before,a.processing,a.after)]
    if path.exists() or path in protected: raise ValueError('Use a new separate report')
    result=evaluate(a.source,a.output,a.before,a.processing,a.after,a.quality_review)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as handle: json.dump(result,handle,ensure_ascii=False,indent=2)
    print(json.dumps({'report':str(path),'state':result['state'],
        'removal_verified_for_this_file':result['removal_verified_for_this_file']},ensure_ascii=False))
    return 0 if result['removal_verified_for_this_file'] else 2

if __name__=='__main__':
    try: sys.exit(main())
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(json.dumps({'error':str(exc),'removal_verified_for_this_file':False}),file=sys.stderr)
        sys.exit(2)
